import logging
from collections.abc import Iterable
from uuid import UUID

from users.models import User

from community.cohosts.invite_helpers import (
    invite_cohosts_and_notify,
    rescind_pending_cohost_invite,
)
from community.models import (
    AssignmentStatus,
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    PlanningSlot,
    PlanningYear,
    SlotAssignment,
)
from community.planning.schemas import AssignmentOut, PlanningSlotOut, PlanningYearOut
from community.validation import Code, ValidationException, raise_validation

logger = logging.getLogger("pda.community.planning_event_link")

ACTIVE_STATUSES = (AssignmentStatus.PROPOSED, AssignmentStatus.COMMITTED)
# Drafts hold a cell for the coordinator but stay invisible to the planner until sent.
HELD_STATUSES = (AssignmentStatus.DRAFT, *ACTIVE_STATUSES)


def get_year_or_404(year: int) -> PlanningYear:
    try:
        return PlanningYear.objects.get(year=year)
    except PlanningYear.DoesNotExist:
        raise_validation(Code.Planning.YEAR_NOT_FOUND, status_code=404)


def year_out(planning_year: PlanningYear) -> PlanningYearOut:
    return PlanningYearOut(
        id=str(planning_year.id),
        year=planning_year.year,
        availability_opened_at=planning_year.availability_opened_at,
    )


def get_slot_or_404(slot_id: UUID) -> PlanningSlot:
    try:
        return PlanningSlot.objects.select_related("event").get(pk=slot_id)
    except PlanningSlot.DoesNotExist:
        raise_validation(Code.Planning.SLOT_NOT_FOUND, status_code=404)


def get_assignment_or_404(
    assignment_id: UUID, owner: User | None = None, *, lock: bool = False
) -> SlotAssignment:
    """param owner(User | None): when set, someone else's row is a 404 too
    param lock(bool): select_for_update; the caller must be inside transaction.atomic()
    """
    rows = SlotAssignment.objects.select_related("slot", "user")
    if lock:
        rows = rows.select_for_update(of=("self",))
    if owner is not None:
        rows = rows.filter(user=owner)
    assignment = rows.filter(pk=assignment_id).first()
    if assignment is None:
        raise_validation(Code.Planning.ASSIGNMENT_NOT_FOUND, status_code=404)
    return assignment


def slot_out(slot: PlanningSlot) -> PlanningSlotOut:
    event = slot.live_event
    return PlanningSlotOut(
        id=str(slot.id),
        label=slot.label,
        month=slot.month,
        kind=slot.kind,
        order=slot.order,
        event_id=str(event.id) if event else None,
        event_slug=event.slug if event else None,
        event_status=event.status if event else None,
    )


def assignment_out(assignment: SlotAssignment) -> AssignmentOut:
    return AssignmentOut(
        id=str(assignment.id),
        slot_id=str(assignment.slot_id),
        user_id=str(assignment.user_id),
        status=assignment.status,
        proposed_at=assignment.proposed_at,
        responded_at=assignment.responded_at,
    )


def invite_planners_to_event(event: Event, planner_ids: Iterable, inviter) -> None:
    """Best-effort: the link or commit has already succeeded, so a rejected invite must not undo it."""
    ids = [str(pk) for pk in planner_ids]
    removed = EventCoHostInvite.objects.filter(
        event=event, user_id__in=ids, status=CoHostInviteStatus.REMOVED
    ).values_list("user_id", flat=True)
    removed_ids = {str(pk) for pk in removed}
    for planner_id in ids:
        # add_cohost_invites would revive a host's removal back to pending
        if planner_id in removed_ids:
            continue
        try:
            invite_cohosts_and_notify(event, [planner_id], inviter)
        except ValidationException:
            logger.warning("planning_cohost_invite_rejected", exc_info=True)


def rescind_planner_invite(slot: PlanningSlot, planner_id) -> None:
    event = slot.live_event
    if event is not None:
        rescind_pending_cohost_invite(event, planner_id)
