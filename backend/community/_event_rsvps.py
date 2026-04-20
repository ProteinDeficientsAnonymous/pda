"""RSVP endpoints for events."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from community._event_helpers import (
    _attending_headcount_db,
    _can_see_invite_only,
    _event_out,
    promote_from_waitlist,
)
from community._event_schemas import EventOut, RSVPIn
from community._events import _can_edit_event
from community._shared import ErrorOut
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus

router = Router()


def _validate_rsvp_access(
    user, event, co_host_ids: set[str], invited_user_ids: set[str]
) -> Status | None:
    """Return an error Status if the user cannot RSVP on this event, else None."""
    if event.visibility == PageVisibility.INVITE_ONLY:
        if not _can_see_invite_only(user, co_host_ids, invited_user_ids, event.created_by_id):
            return Status(404, ErrorOut(detail="Event not found."))
    if not event.rsvp_enabled:
        return Status(400, ErrorOut(detail="RSVPs are not enabled for this event."))
    if event.is_cancelled:
        return Status(400, ErrorOut(detail="RSVPs are closed for cancelled events."))
    if event.is_past and not _can_edit_event(user, event):
        return Status(400, ErrorOut(detail="RSVPs are closed for past events."))
    return None


def _resolve_rsvp_status(
    event: Event, user, requested_status: str, has_plus_one: bool
) -> tuple[str, bool] | Status:
    """Resolve final RSVP status accounting for capacity limits.

    Returns (status, has_plus_one) or a Status error if the +1 is denied.
    """
    if requested_status != RSVPStatus.ATTENDING or event.max_attendees is None:
        return requested_status, has_plus_one

    headcount = _attending_headcount_db(event, exclude_user=user)
    new_spots = 1 + (1 if has_plus_one else 0)

    if headcount + new_spots <= event.max_attendees:
        return requested_status, has_plus_one

    # Over capacity — check if user is already attending (just toggling +1)
    existing = EventRSVP.objects.filter(event=event, user=user).first()
    if existing and existing.status == RSVPStatus.ATTENDING:
        if has_plus_one:
            return Status(400, ErrorOut(detail="No spots available for a +1."))
        # Removing +1 is always fine
        return requested_status, has_plus_one

    # New attending RSVP at capacity — auto-waitlist
    return RSVPStatus.WAITLISTED, False


def _validate_rsvp_status(status: str) -> Status | None:
    """Validate the requested RSVP status. Returns a Status error or None."""
    if status == RSVPStatus.WAITLISTED:
        return Status(400, ErrorOut(detail="Invalid status."))
    valid_statuses = {RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.CANT_GO}
    if status not in valid_statuses:
        return Status(
            400, ErrorOut(detail=f"Status must be one of: {', '.join(sorted(valid_statuses))}.")
        )
    return None


def _apply_rsvp_in_transaction(event_id, user, status: str, has_plus_one: bool):
    """Execute RSVP upsert inside a locked transaction. Returns final_status or Status."""
    event = Event.objects.select_for_update().get(id=event_id)
    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    invited_user_ids = {str(u.id) for u in event.invited_users.all()}

    if err := _validate_rsvp_access(user, event, co_host_ids, invited_user_ids):
        return err

    result = _resolve_rsvp_status(event, user, status, has_plus_one)
    if isinstance(result, Status):
        return result
    final_status, final_plus_one = result

    existing = EventRSVP.objects.filter(event=event, user=user).first()
    was_attending = existing is not None and existing.status == RSVPStatus.ATTENDING
    had_plus_one = existing is not None and existing.has_plus_one

    EventRSVP.objects.update_or_create(
        event=event,
        user=user,
        defaults={"status": final_status, "has_plus_one": final_plus_one},
    )

    spot_freed = (was_attending and final_status != RSVPStatus.ATTENDING) or (
        was_attending and had_plus_one and not final_plus_one
    )
    if spot_freed:
        promote_from_waitlist(event)

    return final_status


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    if err := _validate_rsvp_status(payload.status):
        return err

    with transaction.atomic():
        result = _apply_rsvp_in_transaction(
            event_id, request.auth, payload.status, payload.has_plus_one
        )

    if isinstance(result, Status):
        return result
    final_status = result

    audit_log(
        logging.INFO,
        "rsvp_changed",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"status": final_status},
    )
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/rsvp/",
    response={204: None, 400: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_rsvp(request, event_id: UUID):
    try:
        Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    with transaction.atomic():
        event = Event.objects.select_for_update().prefetch_related("co_hosts").get(id=event_id)
        if event.is_cancelled:
            return Status(400, ErrorOut(detail="RSVPs are closed for cancelled events."))
        if event.is_past and not _can_edit_event(request.auth, event):
            return Status(400, ErrorOut(detail="RSVPs are closed for past events."))
        rsvp = EventRSVP.objects.filter(event=event, user=request.auth).first()
        if not rsvp:
            return Status(404, ErrorOut(detail="RSVP not found."))
        was_attending = rsvp.status == RSVPStatus.ATTENDING
        rsvp.delete()
        if was_attending:
            promote_from_waitlist(event)

    audit_log(logging.INFO, "rsvp_deleted", request, target_type="event", target_id=str(event_id))
    return Status(204, None)
