import logging
from datetime import timedelta
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status

from community._event_helpers import (
    _cancellations,
    _event_out,
    load_event_with_stats_prefetch,
)
from community._event_schemas import AttendanceIn, EventOut, EventStatsOut, TextRecipientsOut
from community._events import _can_edit_event
from community._join_request_approval import _maybe_promote_tentative, send_join_approval
from community._rsvp_counts import (
    _attended_count,
    _attending_headcount,
    _cant_go_count,
    _maybe_count,
    _no_response_count,
    _no_show_count,
    _not_marked_count,
    _waitlisted_count,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus

router = Router()

CHECK_IN_OPENS_BEFORE_START = timedelta(hours=1)


def _check_in_open(event: Event) -> bool:
    """Check-in opens 1 hour before start and never closes."""
    if event.start_datetime is None:
        return False
    return timezone.now() >= event.start_datetime - CHECK_IN_OPENS_BEFORE_START


@router.get(
    "/events/{event_id}/stats/",
    response={200: EventStatsOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_event_stats(request, event_id: UUID):
    event = load_event_with_stats_prefetch(event_id)
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
            cancellations=_cancellations(event, request.auth),
        ),
    )


def _build_text_recipients(event: Event) -> TextRecipientsOut:
    by_status: dict[str, list[str]] = {
        RSVPStatus.ATTENDING: [],
        RSVPStatus.MAYBE: [],
        RSVPStatus.CANT_GO: [],
        RSVPStatus.WAITLISTED: [],
    }
    for rsvp in event.rsvps.all():
        phone = rsvp.user.phone_number
        if phone and rsvp.status in by_status:
            by_status[rsvp.status].append(phone)
    invited = [u.phone_number for u in event.invited_users.all() if u.phone_number]
    return TextRecipientsOut(
        attending=by_status[RSVPStatus.ATTENDING],
        maybe=by_status[RSVPStatus.MAYBE],
        cant_go=by_status[RSVPStatus.CANT_GO],
        waitlisted=by_status[RSVPStatus.WAITLISTED],
        invited=invited,
    )


@router.get(
    "/events/{event_id}/text-recipients/",
    response={200: TextRecipientsOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_text_recipients(request, event_id: UUID):
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="get_text_recipients")
    return Status(200, _build_text_recipients(event))


@router.post(
    "/events/{event_id}/rsvps/{user_id}/attendance/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
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

    # The mark and any tentative promotion it triggers commit as a unit, so a
    # mid-promotion failure can't leave a member flagged without their request
    # stamped approved.
    with transaction.atomic():
        rsvp.attendance = payload.attendance
        # Stamp the first time a guest is marked ATTENDED; keep the original
        # check-in time if attendance is later flipped and re-marked.
        if payload.attendance == AttendanceStatus.ATTENDED and rsvp.checked_in_at is None:
            rsvp.checked_in_at = timezone.now()
        rsvp.save(update_fields=["attendance", "checked_in_at", "updated_at"])
        promoted = payload.attendance == AttendanceStatus.ATTENDED and _maybe_promote_tentative(
            rsvp.user, event, request.auth
        )

    if promoted:
        send_join_approval(
            to=rsvp.user.email,
            display_name=rsvp.user.full_name,
            first_name=rsvp.user.first_name,
        )

    audit_log(
        logging.INFO,
        "attendance_marked",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user_id), "attendance": payload.attendance},
    )

    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return Status(200, _event_out(event, request.auth))
