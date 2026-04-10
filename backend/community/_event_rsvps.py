"""RSVP endpoints for events."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from community._event_helpers import _can_see_invite_only, _event_out
from community._event_schemas import EventOut, RSVPIn
from community._events import _can_edit_event
from community._shared import ErrorOut
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus

router = Router()


def _validate_rsvp_access(user, event) -> Status | None:
    """Return an error Status if the user cannot RSVP on this event, else None."""
    if event.visibility == PageVisibility.INVITE_ONLY:
        co_host_ids = {str(c.id) for c in event.co_hosts.all()}
        invited_user_ids = {str(u.id) for u in event.invited_users.all()}
        if not _can_see_invite_only(user, co_host_ids, invited_user_ids, event.created_by_id):
            return Status(404, ErrorOut(detail="Event not found."))
    if not event.rsvp_enabled:
        return Status(400, ErrorOut(detail="RSVPs are not enabled for this event."))
    if event.is_cancelled:
        return Status(400, ErrorOut(detail="RSVPs are closed for cancelled events."))
    if event.is_past and not _can_edit_event(user, event):
        return Status(400, ErrorOut(detail="RSVPs are closed for past events."))
    return None


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    if err := _validate_rsvp_access(request.auth, event):
        return err

    valid_statuses = RSVPStatus.values
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    EventRSVP.objects.update_or_create(
        event=event,
        user=request.auth,
        defaults={"status": payload.status, "has_plus_one": payload.has_plus_one},
    )
    audit_log(
        logging.INFO,
        "rsvp_changed",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"status": payload.status},
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
        event = Event.objects.prefetch_related("co_hosts").get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    if event.is_cancelled:
        return Status(400, ErrorOut(detail="RSVPs are closed for cancelled events."))
    if event.is_past and not _can_edit_event(request.auth, event):
        return Status(400, ErrorOut(detail="RSVPs are closed for past events."))
    deleted, _ = EventRSVP.objects.filter(event_id=event_id, user=request.auth).delete()
    if not deleted:
        return Status(404, ErrorOut(detail="RSVP not found."))
    audit_log(logging.INFO, "rsvp_deleted", request, target_type="event", target_id=str(event_id))
    return Status(204, None)
