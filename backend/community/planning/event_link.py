import logging
from collections.abc import Iterable
from uuid import UUID

from config.auth import gated_jwt
from django.db import transaction
from ninja import Router
from pydantic import BaseModel

from community.cohosts.invite_helpers import (
    invite_cohosts_and_notify,
    rescind_pending_cohost_invite,
)
from community.models import (
    AssignmentStatus,
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventStatus,
    PlanningSlot,
)
from community.planning._access import require_manage_or
from community.planning.schemas import PlanningSlotOut
from community.planning.years import slot_out
from community.shared import ErrorOut
from community.validation import Code, ValidationException, raise_validation

router = Router()
logger = logging.getLogger("pda.community.planning_event_link")


class LinkEventIn(BaseModel):
    event_id: UUID


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


@router.post(
    "/planning/slots/{slot_id}/event/",
    response={200: PlanningSlotOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def link_slot_event(request, slot_id: UUID, payload: LinkEventIn):
    user = request.auth
    with transaction.atomic():
        slot = (
            PlanningSlot.objects.select_for_update(of=("self",))
            .select_related("event")
            .filter(pk=slot_id)
            .first()
        )
        if slot is None:
            raise_validation(Code.Planning.SLOT_NOT_FOUND, status_code=404)
        committed = slot.assignments.filter(status=AssignmentStatus.COMMITTED)
        require_manage_or(request, "link_planning_slot_event", committed.filter(user=user).exists())
        event = (
            Event.objects.select_for_update(of=("self",))
            .exclude(status=EventStatus.DELETED)
            .filter(pk=payload.event_id)
            .first()
        )
        if event is None:
            raise_validation(Code.Event.NOT_FOUND, status_code=404)
        if slot.live_event is not None:
            raise_validation(Code.Planning.SLOT_HAS_EVENT, status_code=400)
        if not event.co_hosts.filter(pk=user.pk).exists():
            raise_validation(Code.Planning.NOT_EVENT_HOST, status_code=400)
        if PlanningSlot.objects.filter(event=event).exclude(pk=slot.pk).exists():
            raise_validation(Code.Planning.EVENT_ALREADY_LINKED, status_code=400)
        slot.event = event
        slot.save(update_fields=["event"])
        teammate_ids = list(committed.exclude(user=user).values_list("user_id", flat=True))
    invite_planners_to_event(event, teammate_ids, user)
    return slot_out(slot)
