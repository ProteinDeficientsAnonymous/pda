import logging
from datetime import timedelta
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Router
from ninja.responses import Status

from community.events.helpers import (
    can_edit_event,
    cancellations,
    event_out,
    load_editable_event,
    load_event_with_stats_prefetch,
)
from community.events.schemas import (
    AttendanceIn,
    EventOut,
    EventStatsOut,
    TextRecipientsOut,
)
from community.join_requests.approval import send_join_approval
from community.join_requests.check_in_promotion import (
    CheckInOutcome,
    notify_member_restored,
    promote_or_restore_on_check_in,
    send_member_restored,
)
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus
from community.rsvps.counts import (
    attending_headcount,
    count_attended,
    count_cant_go,
    count_didnt_go,
    count_maybe,
    count_no_response,
    count_not_marked,
    count_waitlisted,
)
from community.shared import ErrorOut
from community.validation import Code, raise_validation

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
    if not can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="get_event_stats")
    return Status(
        200,
        EventStatsOut(
            going_count=attending_headcount(event),
            maybe_count=count_maybe(event),
            cant_go_count=count_cant_go(event),
            no_response_count=count_no_response(event),
            waitlisted_count=count_waitlisted(event),
            attended_count=count_attended(event),
            didnt_go_count=count_didnt_go(event),
            not_marked_count=count_not_marked(event),
            cancellations=cancellations(event, request.auth),
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
    if not can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="get_text_recipients")
    return Status(200, _build_text_recipients(event))


def _apply_attendance_mark(
    request, rsvp: EventRSVP, payload: AttendanceIn
) -> CheckInOutcome | None:
    """Persist the attendance mark, promoting or restoring a non-member if it was a check-in.

    return(CheckInOutcome | None): what the check-in did to the guest's membership, if anything.
    """
    attendance_field, checked_in_field = (
        ("plus_one_attendance", "plus_one_checked_in_at")
        if payload.for_plus_one
        else ("attendance", "checked_in_at")
    )
    setattr(rsvp, attendance_field, payload.attendance)
    # Stamp the first time a guest is marked ATTENDED; keep the original
    # check-in time if attendance is later flipped and re-marked.
    if payload.attendance == AttendanceStatus.ATTENDED and getattr(rsvp, checked_in_field) is None:
        setattr(rsvp, checked_in_field, timezone.now())
    rsvp.save(update_fields=[attendance_field, checked_in_field, "updated_at"])

    if payload.attendance != AttendanceStatus.ATTENDED or payload.for_plus_one:
        return None
    return promote_or_restore_on_check_in(request, rsvp.user, rsvp.event)


@router.post(
    "/events/{event_id}/rsvps/{user_id}/attendance/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="60/m")
def set_attendance(request, event_id: UUID, user_id: UUID, payload: AttendanceIn):
    event = load_editable_event(request.auth, event_id, "set_attendance")
    if not _check_in_open(event):
        raise_validation(Code.Event.ATTENDANCE_OPENS_LATER, status_code=400)

    rsvp = event.rsvps.select_related("user").filter(user_id=user_id).first()
    if rsvp is None:
        raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
    if payload.for_plus_one and not rsvp.has_plus_one:
        raise_validation(Code.Event.NO_PLUS_ONE_TO_CHECK_IN, status_code=400)

    # A failed promotion or restore rolls back in its own savepoint; the mark stays.
    with transaction.atomic():
        outcome = _apply_attendance_mark(request, rsvp, payload)

    if outcome == CheckInOutcome.PROMOTED:
        send_join_approval(
            to=rsvp.user.email,
            display_name=rsvp.user.full_name,
            first_name=rsvp.user.first_name,
        )
    elif outcome == CheckInOutcome.RESTORED:
        send_member_restored(rsvp.user)
        notify_member_restored(rsvp.user)

    audit_log(
        logging.INFO,
        "attendance_marked",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={
                "user_id": str(user_id),
                "attendance": payload.attendance,
                "for_plus_one": payload.for_plus_one,
            },
        ),
    )

    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return Status(200, event_out(event, request.auth))
