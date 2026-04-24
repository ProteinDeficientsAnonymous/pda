"""RSVP endpoints for events."""

import logging
from datetime import timedelta
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from community._event_helpers import (
    _attended_count,
    _attending_headcount,
    _attending_headcount_db,
    _can_see_invite_only,
    _cancellations,
    _cant_go_count,
    _event_out,
    _maybe_count,
    _no_response_count,
    _no_show_count,
    _not_marked_count,
    _waitlisted_count,
    promote_from_waitlist,
)
from community._event_schemas import AttendanceIn, EventOut, EventStatsOut, RSVPIn
from community._events import _can_edit_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus

router = Router()

CHECK_IN_OPENS_BEFORE_START = timedelta(hours=1)


def _check_in_open(event: Event) -> bool:
    """Check-in opens 1 hour before start and never closes."""
    if event.start_datetime is None:
        return False
    return timezone.now() >= event.start_datetime - CHECK_IN_OPENS_BEFORE_START


def _validate_rsvp_access(user, event, co_host_ids: set[str], invited_user_ids: set[str]) -> None:
    """Raise ValidationException if the user cannot RSVP on this event."""
    if event.visibility == PageVisibility.INVITE_ONLY:
        if not _can_see_invite_only(user, co_host_ids, invited_user_ids, event.created_by_id):
            raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)
    if event.is_past and not _can_edit_event(user, event):
        raise_validation(Code.Event.RSVPS_CLOSED_PAST, status_code=400)


def _resolve_rsvp_status(
    event: Event, user, requested_status: str, has_plus_one: bool
) -> tuple[str, bool]:
    """Resolve final RSVP status accounting for capacity limits.

    Returns (status, has_plus_one). Raises ValidationException if a +1 is
    denied at capacity.
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
            raise_validation(Code.Event.NO_PLUS_ONE_SPOTS, status_code=400)
        # Removing +1 is always fine
        return requested_status, has_plus_one

    # New attending RSVP at capacity — auto-waitlist
    return RSVPStatus.WAITLISTED, False


def _validate_rsvp_status(status: str) -> None:
    """Raise ValidationException if the requested RSVP status is invalid."""
    valid_statuses = {RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.CANT_GO}
    if status == RSVPStatus.WAITLISTED or status not in valid_statuses:
        raise_validation(
            Code.Event.RSVP_INVALID_STATUS,
            field="status",
            status_code=400,
            allowed=sorted(valid_statuses),
        )


def _apply_rsvp_in_transaction(event_id, user, status: str, has_plus_one: bool) -> str:
    """Execute RSVP upsert inside a locked transaction. Returns final_status.

    Raises ValidationException on failure.
    """
    event = Event.objects.select_for_update().get(id=event_id)
    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    invited_user_ids = {str(u.id) for u in event.invited_users.all()}

    _validate_rsvp_access(user, event, co_host_ids, invited_user_ids)

    final_status, final_plus_one = _resolve_rsvp_status(event, user, status, has_plus_one)

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
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        final_status = _apply_rsvp_in_transaction(
            event_id, request.auth, payload.status, payload.has_plus_one
        )

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


def _load_event_with_stats_prefetch(event_id: UUID) -> Event | None:
    return (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )


@router.get(
    "/events/{event_id}/stats/",
    response={200: EventStatsOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_event_stats(request, event_id: UUID):
    event = _load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="get_event_stats")
    return Status(
        200,
        EventStatsOut(
            going_count=_attending_headcount(event),
            maybe_count=_maybe_count(event),
            cant_go_count=_cant_go_count(event),
            no_response_count=_no_response_count(event),
            waitlisted_count=_waitlisted_count(event),
            attended_count=_attended_count(event),
            no_show_count=_no_show_count(event),
            not_marked_count=_not_marked_count(event),
            cancellations=_cancellations(event),
        ),
    )


@router.post(
    "/events/{event_id}/rsvps/{user_id}/attendance/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="60/m")
def set_attendance(request, event_id: UUID, user_id: UUID, payload: AttendanceIn):
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="set_attendance")
    if not _check_in_open(event):
        raise_validation(Code.Event.ATTENDANCE_OPENS_LATER, status_code=400)

    rsvp = EventRSVP.objects.filter(event=event, user_id=user_id).first()
    if rsvp is None:
        raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
    if rsvp.status != RSVPStatus.ATTENDING:
        raise_validation(Code.Event.ATTENDANCE_ONLY_FOR_GOING_RSVPS, status_code=400)

    rsvp.attendance = payload.attendance
    rsvp.save(update_fields=["attendance", "updated_at"])

    audit_log(
        logging.INFO,
        "attendance_marked",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user_id), "attendance": payload.attendance},
    )

    event = _load_event_with_stats_prefetch(event_id)
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
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    with transaction.atomic():
        event = Event.objects.select_for_update().prefetch_related("co_hosts").get(id=event_id)
        if event.is_cancelled:
            raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)
        if event.is_past and not _can_edit_event(request.auth, event):
            raise_validation(Code.Event.RSVPS_CLOSED_PAST, status_code=400)
        rsvp = EventRSVP.objects.filter(event=event, user=request.auth).first()
        if not rsvp:
            raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
        was_attending = rsvp.status == RSVPStatus.ATTENDING
        rsvp.delete()
        if was_attending:
            promote_from_waitlist(event)

    audit_log(logging.INFO, "rsvp_deleted", request, target_type="event", target_id=str(event_id))
    return Status(204, None)
