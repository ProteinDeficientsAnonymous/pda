import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status

from community._event_helpers import (
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
)
from community._event_schemas import EventOut, WaitlistOrderIn
from community._events import _can_edit_event
from community._public_rsvp_shared import _email_promoted_non_members
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community._waitlist import promote_from_waitlist
from community.models import Event, EventRSVP, RSVPStatus

router = Router()


@router.put(
    "/events/{event_id}/waitlist/order/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def reorder_waitlist(request, event_id: UUID, payload: WaitlistOrderIn):
    """Let an event host/co-host/manager set the waitlist order (Issue 1553)."""
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="reorder_waitlist")

    with transaction.atomic():
        promoted_user_ids = _reorder_waitlist_in_transaction(event_id, payload.user_ids)

    audit_log(
        logging.INFO,
        "waitlist_reordered",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={"user_ids": [str(u) for u in payload.user_ids]},
        ),
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))


def _reorder_waitlist_in_transaction(event_id, user_ids: list[UUID]) -> list[str]:
    """Assign positions 1..n in the given order, then promote if the new head now fits.

    user_ids must be exactly the current waitlist; otherwise the host saw a stale list.
    """
    event = Event.objects.select_for_update().get(id=event_id)
    rsvps = {
        r.user_id: r for r in EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED)
    }
    if len(user_ids) != len(set(user_ids)) or set(user_ids) != set(rsvps):
        raise_validation(Code.Event.WAITLIST_ORDER_STALE, status_code=400)

    for position, user_id in enumerate(user_ids, start=1):
        rsvps[user_id].waitlist_position = position
    EventRSVP.objects.bulk_update(rsvps.values(), ["waitlist_position"])
    return promote_from_waitlist(event)
