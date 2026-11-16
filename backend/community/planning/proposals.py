from uuid import UUID

from config.auth import gated_jwt
from django.db import transaction
from ninja import Router
from ninja.responses import Status

from community.models import AssignmentStatus, SlotAssignment
from community.planning._access import require_manage
from community.planning._notify import notify_withdrawn
from community.planning._planners import planner_users
from community.planning._shared import (
    ACTIVE_STATUSES,
    HELD_STATUSES,
    assignment_out,
    get_assignment_or_404,
    get_slot_or_404,
    rescind_planner_invite,
)
from community.planning.schemas import AssignmentOut, ProposeIn
from community.shared import ErrorOut
from community.validation import Code, raise_validation

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
