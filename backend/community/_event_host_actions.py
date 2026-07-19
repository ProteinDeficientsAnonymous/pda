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
from users.models import User as UserModel

from community._event_helpers import (
    _cancellations,
    _event_out,
    broadcast_capacity_change,
    load_event_with_stats_prefetch,
    promote_from_waitlist,
)
from community._event_rsvps import (
    _resolve_cancelled_at,
    _resolve_rsvp_status,
    _validate_rsvp_status,
)
from community._event_schemas import (
    AttendanceIn,
    EventOut,
    EventStatsOut,
    HostRSVPIn,
    TextRecipientsOut,
)
from community._events import _can_edit_event
from community._join_request_approval import _maybe_promote_tentative, send_join_approval
from community._public_rsvp_shared import _email_promoted_non_members
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
        magic_token = (
            _maybe_promote_tentative(rsvp.user, event, request.auth)
            if payload.attendance == AttendanceStatus.ATTENDED
            else None
        )

    if magic_token:
        send_join_approval(
            to=rsvp.user.email,
            display_name=rsvp.user.full_name,
            first_name=rsvp.user.first_name,
            magic_token=magic_token,
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


def _apply_host_rsvp_in_transaction(
    event_id, target_user, status: str, has_plus_one: bool
) -> tuple[str, list[str]]:
    """Execute a host-driven RSVP upsert for another user inside a locked transaction.

    Unlike _apply_rsvp_in_transaction, access is already gated on the acting
    host (_can_edit_event) by the caller — this only enforces that the event
    still accepts RSVPs, not the target user's own read-visibility.

    Returns (final_status, promoted_user_ids). Raises ValidationException on failure.
    """
    event = (
        Event.objects.select_for_update()
        .prefetch_related("co_hosts", "invited_users")
        .get(id=event_id)
    )

    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)

    final_status, final_plus_one = _resolve_rsvp_status(event, target_user, status, has_plus_one)

    existing = EventRSVP.objects.filter(event=event, user=target_user).first()
    was_attending = existing is not None and existing.status == RSVPStatus.ATTENDING
    had_plus_one = existing is not None and existing.has_plus_one

    if (
        existing is not None
        and existing.status == final_status
        and existing.has_plus_one == final_plus_one
    ):
        return final_status, []

    EventRSVP.objects.update_or_create(
        event=event,
        user=target_user,
        defaults={
            "status": final_status,
            "has_plus_one": final_plus_one,
            "cancelled_at": _resolve_cancelled_at(existing, final_status),
        },
    )

    spot_freed = (was_attending and final_status != RSVPStatus.ATTENDING) or (
        was_attending and had_plus_one and not final_plus_one
    )
    promoted_user_ids = promote_from_waitlist(event) if spot_freed else []

    return final_status, promoted_user_ids


@router.post(
    "/events/{event_id}/rsvps/{user_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def set_guest_rsvp(request, event_id: UUID, user_id: UUID, payload: HostRSVPIn):
    """Let an event host/co-host/manager change another user's rsvp on their behalf (Issue 872)."""
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="set_guest_rsvp")

    _validate_rsvp_status(payload.status)

    try:
        target_user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    with transaction.atomic():
        final_status, promoted_user_ids = _apply_host_rsvp_in_transaction(
            event_id, target_user, payload.status, payload.has_plus_one
        )

    audit_log(
        logging.INFO,
        "guest_rsvp_changed",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user_id), "status": final_status},
    )
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    broadcast_capacity_change(event_id, exclude_user_ids={str(request.auth.pk)})
    _email_promoted_non_members(request, event, promoted_user_ids)
    return Status(200, _event_out(event, request.auth))
