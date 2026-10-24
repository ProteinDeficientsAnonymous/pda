from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Exists, Max, OuterRef, Q, QuerySet
from django.utils import timezone
from notifications._email_helpers import send_tentative_attendance_nudge_email
from notifications.email_sender import EmailSender
from users.models import HAS_EMAIL, User

from community._login_reminder import NOT_SET_UP
from community.models import (
    EventRSVP,
    EventStatus,
    EventType,
    JoinRequestStatus,
    RSVPStatus,
    TentativeAttendanceNudge,
)
from community.models.event import _is_past_q

# Just under 1w / 1w / 2w / 4w so a drifting weekly cron lands ~1 week, 2 weeks, 1 month, then monthly.
_FIRST_GAPS = (timedelta(days=6), timedelta(days=6), timedelta(days=13))
_MONTHLY_GAP = timedelta(days=27)
_SIGNED_UP = (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED)


def gap_before(nudge_number: int) -> timedelta:
    if nudge_number <= len(_FIRST_GAPS):
        return _FIRST_GAPS[nudge_number - 1]
    return _MONTHLY_GAP


def _candidates(now: datetime) -> QuerySet:
    upcoming_rsvp = EventRSVP.objects.filter(
        user=OuterRef("pk"),
        status__in=_SIGNED_UP,
        event__event_type__in=(EventType.OFFICIAL, EventType.CLUB),
        event__status=EventStatus.ACTIVE,
    ).exclude(_is_past_q(now, "event__"))
    return (
        User.objects.active_tentative_members()
        .filter(HAS_EMAIL, attendance_nudge_opt_out=False)
        .exclude(NOT_SET_UP)
        .exclude(Exists(upcoming_rsvp))
        .annotate(
            nudge_count=Count("attendance_nudges", distinct=True),
            last_nudged_at=Max("attendance_nudges__sent_at"),
            tentative_at=Max(
                "join_requests__tentative_at",
                filter=Q(join_requests__status=JoinRequestStatus.TENTATIVE),
            ),
        )
    )


def _due_number(user: User, now: datetime) -> int | None:
    # Gaps run from the last send, so a pause for an upcoming rsvp shifts the rest of the schedule.
    anchor = user.last_nudged_at or user.onboarded_at or user.tentative_at  # ty: ignore[unresolved-attribute]
    if anchor is None:
        return None
    number = user.nudge_count + 1  # ty: ignore[unresolved-attribute]
    return number if now - anchor >= gap_before(number) else None


def _claim(user_id, now: datetime) -> TentativeAttendanceNudge | None:
    # Recording before sending, under a row lock, stops an overlapping run from double-sending.
    with transaction.atomic():
        User.objects.select_for_update().filter(pk=user_id).first()
        user = _candidates(now).filter(pk=user_id).first()
        number = _due_number(user, now) if user else None
        if number is None:
            return None
        return TentativeAttendanceNudge.objects.create(user=user, nudge_number=number)


def send_attendance_nudges(sender: EmailSender) -> tuple[int, int]:
    """Nudge tentative members who haven't signed up for an official or club event yet.

    return(tuple[int, int]): (sent, failed) counts
    """
    now = timezone.now()
    calendar_url = f"{settings.FRONTEND_BASE_URL}/calendar"
    settings_url = f"{settings.FRONTEND_BASE_URL}/settings"
    sent = failed = 0
    for user in _candidates(now):
        if _due_number(user, now) is None:
            continue
        nudge = _claim(user.pk, now)
        if nudge is None:
            continue
        result = send_tentative_attendance_nudge_email(
            sender=sender,
            to=user.email,
            display_name=user.first_name,
            calendar_url=calendar_url,
            settings_url=settings_url,
        )
        if result.success:
            sent += 1
        else:
            nudge.delete()
            failed += 1
    return sent, failed
