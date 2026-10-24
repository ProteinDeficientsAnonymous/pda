from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from notifications._event_feedback_email import send_event_feedback_email
from notifications.email_sender import EmailStream, SendResult, get_email_sender

from community.models import (
    AttendanceStatus,
    Event,
    EventFeedbackRequest,
    EventRSVP,
    EventStatus,
    Survey,
)
from community.models.event import _is_past_q

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from notifications.email_sender import EmailSender

logger = logging.getLogger(__name__)

FEEDBACK_LOOKBACK = timedelta(days=7)
REMINDER_AFTER_DAYS = 3


def _local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=settings.COMMUNITY_TZ)


def feedback_cutoff(now: datetime) -> datetime:
    """Start of `now`'s local date in COMMUNITY_TZ."""
    return _local_midnight(timezone.localtime(now, settings.COMMUNITY_TZ).date())


def feedback_url(token: str) -> str:
    # Fragment: browsers never send it, so the token stays out of server request logs.
    return f"{settings.FRONTEND_BASE_URL}/feedback#{token}"


def _active_feedback_event_types() -> list[str]:
    return list(
        Survey.objects.filter(is_active=True)
        .exclude(feedback_event_type="")
        .values_list("feedback_event_type", flat=True)
    )


def due_feedback_events(now: datetime) -> QuerySet[Event]:
    cutoff = feedback_cutoff(now)
    return Event.objects.filter(
        _is_past_q(cutoff),
        ~_is_past_q(cutoff - FEEDBACK_LOOKBACK),
        status=EventStatus.ACTIVE,
        event_type__in=_active_feedback_event_types(),
    )


def _event_date_label(event: Event) -> str | None:
    if event.start_datetime is None:
        return None
    local = timezone.localtime(event.start_datetime, settings.COMMUNITY_TZ)
    return f"{local:%b} {local.day}".lower()


def _send(
    sender: EmailSender, request: EventFeedbackRequest, *, reminder: bool
) -> SendResult | None:
    user = request.user
    try:
        result = send_event_feedback_email(
            sender=sender,
            to=user.email or "",
            display_name=user.first_name or "",
            event_title=request.event.title,
            event_date=_event_date_label(request.event),
            url=feedback_url(request.token),
            reminder=reminder,
        )
    except Exception:  # noqa: BLE001 — one bad send must not abort the batch
        logger.warning("event_feedback_email_send_exception", exc_info=True)
        return None
    if not result.success:
        logger.warning("event_feedback_email_failed", extra={"error": result.error})
    return result


def _create_request(event: Event, rsvp: EventRSVP) -> EventFeedbackRequest | None:
    try:
        with transaction.atomic():
            request, created = EventFeedbackRequest.objects.get_or_create(
                event=event,
                user=rsvp.user,
                defaults={"token": EventFeedbackRequest.new_token()},
            )
    except IntegrityError:
        return None
    return request if created else None


def _send_first_for_event(sender: EmailSender, event: Event, now: datetime) -> int:
    requested = EventFeedbackRequest.objects.filter(event=event).values("user_id")
    rsvps = (
        EventRSVP.objects.filter(event=event, attendance=AttendanceStatus.ATTENDED)
        .exclude(user_id__in=requested)
        .select_related("user")
    )
    sent = 0
    for rsvp in rsvps:
        request = _create_request(event, rsvp)
        if request is None or not rsvp.user.email:
            continue
        result = _send(sender, request, reminder=False)
        if result is not None and result.success:
            EventFeedbackRequest.objects.filter(pk=request.pk).update(first_sent_at=now)
            sent += 1
    return sent


def send_first_requests(now: datetime) -> int:
    """Email a feedback link to each checked-in attendee without a request yet. Returns emails sent."""
    sender = get_email_sender(EmailStream.BULK)
    return sum(_send_first_for_event(sender, event, now) for event in due_feedback_events(now))


def send_reminders(now: datetime) -> int:
    """Send the single reminder to non-responders three local days after the first email."""
    first_sent_before = _local_midnight(
        timezone.localtime(now, settings.COMMUNITY_TZ).date()
        - timedelta(days=REMINDER_AFTER_DAYS - 1)
    )
    due = EventFeedbackRequest.objects.filter(
        first_sent_at__lt=first_sent_before,
        reminder_sent_at__isnull=True,
        responded_on__isnull=True,
        event__status=EventStatus.ACTIVE,
        event__event_type__in=_active_feedback_event_types(),
    ).select_related("event", "user")
    sender = get_email_sender(EmailStream.BULK)
    sent = 0
    for request in due:
        if not request.user.email:
            continue
        claimed = EventFeedbackRequest.objects.filter(
            pk=request.pk, reminder_sent_at__isnull=True
        ).update(reminder_sent_at=now)
        if claimed != 1:
            continue
        result = _send(sender, request, reminder=True)
        if result is not None and result.success:
            sent += 1
    return sent
