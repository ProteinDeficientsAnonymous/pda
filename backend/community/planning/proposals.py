import logging
from uuid import UUID

from config.auth import gated_jwt
from django.db import transaction
from django.db.models import QuerySet
from ninja import Router
from ninja.responses import Status
from users.models import User

from community.models import AssignmentStatus, SlotAssignment
from community.planning._access import require_manage
from community.planning._notify import notify_confirmed, notify_proposed, notify_withdrawn
from community.planning._planners import planner_users
from community.planning._shared import (
    ACTIVE_STATUSES,
    HELD_STATUSES,
    assignment_out,
    get_assignment_or_404,
    get_slot_or_404,
    get_year_or_404,
    invite_planners_to_event,
    rescind_planner_invite,
)
from community.planning.schemas import AssignmentOut, ProposalsSentOut, ProposeIn
from community.shared import ErrorOut
from community.validation import Code, raise_validation

logger = logging.getLogger(__name__)

router = Router()


@router.post(
    "/planning/slots/{slot_id}/assignments/",
    response={201: AssignmentOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def propose_assignment(request, slot_id: UUID, payload: ProposeIn):
    require_manage(request, "propose_planning_assignment")
    slot = get_slot_or_404(slot_id)
    user = planner_users().filter(pk=payload.user_id).first()
    if user is None:
        raise_validation(Code.Planning.NOT_A_PLANNER, field="user_id", status_code=400)
    assignment, created = SlotAssignment.objects.get_or_create(
        slot=slot,
        user=user,
        defaults={"proposed_by": request.auth, "status": AssignmentStatus.DRAFT},
    )
    if not created:
        if assignment.status in HELD_STATUSES:
            raise_validation(Code.Planning.ALREADY_ASSIGNED, field="user_id", status_code=400)
        assignment.stage(request.auth)
    return Status(201, assignment_out(assignment))


@router.post(
    "/planning/slots/{slot_id}/assignments/confirm/",
    response={201: AssignmentOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def confirm_assignment(request, slot_id: UUID, payload: ProposeIn):
    require_manage(request, "confirm_planning_assignment")
    slot = get_slot_or_404(slot_id)
    user = planner_users().filter(pk=payload.user_id).first()
    if user is None:
        raise_validation(Code.Planning.NOT_A_PLANNER, field="user_id", status_code=400)
    with transaction.atomic():
        assignment, _ = SlotAssignment.objects.select_for_update(of=("self",)).get_or_create(
            slot=slot, user=user, defaults={"status": AssignmentStatus.DRAFT}
        )
        if assignment.status == AssignmentStatus.COMMITTED:
            raise_validation(Code.Planning.ALREADY_ASSIGNED, field="user_id", status_code=400)
        assignment.confirm(request.auth)
        if user != request.auth:
            notify_confirmed(assignment, request.auth)
    event = slot.live_event
    if event is not None:
        invite_planners_to_event(event, [user.pk], event.created_by or request.auth)
    return Status(201, assignment_out(assignment))


@router.post(
    "/planning/years/{year}/proposals/send/",
    response={200: ProposalsSentOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def send_proposals(request, year: int):
    require_manage(request, "send_planning_proposals")
    drafts = SlotAssignment.objects.filter(
        slot__planning_year=get_year_or_404(year),
        status=AssignmentStatus.DRAFT,
        user__in=planner_users(),
    )
    planner_ids = list(drafts.order_by().values_list("user_id", flat=True).distinct())
    notified = sent = 0
    for user_id in planner_ids:
        try:
            count = _send_planner_drafts(drafts, user_id, request.auth)
        except Exception:  # noqa: BLE001 — one planner's failure must not block the rest
            logger.exception("planning_send_failed", extra={"user": user_id})
            continue
        if count:
            notified += 1
            sent += count
    return ProposalsSentOut(planners_notified=notified, proposals_sent=sent)


def _send_planner_drafts(drafts: QuerySet[SlotAssignment], user_id: UUID, by: User) -> int:
    # One transaction per planner: a failed notice un-sends only that planner's drafts.
    with transaction.atomic():
        mine = list(
            drafts.filter(user_id=user_id)
            .select_for_update(of=("self",))
            .select_related("slot", "user")
            .order_by("slot__order")
        )
        for draft in mine:
            draft.propose(by)
        if mine:
            notify_proposed(mine[0].user, [d.slot for d in mine], by)
    return len(mine)


@router.delete(
    "/planning/assignments/{assignment_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def withdraw_assignment(request, assignment_id: UUID):
    require_manage(request, "withdraw_planning_assignment")
    with transaction.atomic():
        assignment = get_assignment_or_404(assignment_id, lock=True)
        was_active = assignment.status in ACTIVE_STATUSES
        was_committed = assignment.status == AssignmentStatus.COMMITTED
        if assignment.status in HELD_STATUSES:
            assignment.withdraw()
    if was_active:
        notify_withdrawn(assignment, request.auth)
    if was_committed:
        rescind_planner_invite(assignment.slot, assignment.user_id)
    return Status(204, None)
