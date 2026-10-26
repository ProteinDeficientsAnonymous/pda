from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from django.conf import settings
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


def _requests_by_user(event: Event, user_ids: list[UUID]) -> dict[UUID, EventFeedbackRequest]:
    existing = EventFeedbackRequest.objects.filter(event=event, user_id__in=user_ids)
    by_user = {r.user_id: r for r in existing}
    missing = [
        EventFeedbackRequest(event=event, user_id=uid, token=EventFeedbackRequest.new_token())
        for uid in user_ids
        if uid not in by_user
    ]
    if missing:
        # a concurrent run may have inserted some; re-read so every pk is the stored one
        EventFeedbackRequest.objects.bulk_create(missing, ignore_conflicts=True)
        by_user = {r.user_id: r for r in existing.all()}
    return by_user


def _claim_first_send(request: EventFeedbackRequest, now: datetime) -> bool:
    return (
        EventFeedbackRequest.objects.filter(pk=request.pk, first_sent_at__isnull=True).update(
            first_sent_at=now
        )
        == 1
    )


def _send_first_for_event(sender: EmailSender, event: Event, now: datetime) -> tuple[int, int]:
    rsvps = list(
        EventRSVP.objects.filter(
            event=event,
            attendance=AttendanceStatus.ATTENDED,
            user__is_active=True,
            user__archived_at__isnull=True,
        ).select_related("user")
    )
    requests = _requests_by_user(event, [r.user_id for r in rsvps])
    sent = failed = 0
    for rsvp in rsvps:
        request = requests.get(rsvp.user_id)
        if request is None or request.first_sent_at is not None or not rsvp.user.email:
            continue
        request.event, request.user = event, rsvp.user
        if not _claim_first_send(request, now):
            continue
        result = _send(sender, request, reminder=False)
        if result is not None and result.success:
            sent += 1
        else:
            failed += 1
            EventFeedbackRequest.objects.filter(pk=request.pk).update(first_sent_at=None)
    return sent, failed


def send_first_requests(now: datetime) -> tuple[int, int]:
    """Email a feedback link to each checked-in attendee not yet sent one, retrying failed sends. Returns (sent, failed)."""
    sender = get_email_sender(EmailStream.BULK)
    results = [_send_first_for_event(sender, event, now) for event in due_feedback_events(now)]
    return sum(r[0] for r in results), sum(r[1] for r in results)


def send_reminders(now: datetime) -> tuple[int, int]:
    """Send the single reminder to non-responders three local days after the first email."""
    today = timezone.localtime(now, settings.COMMUNITY_TZ).date()
    first_sent_before = _local_midnight(today - timedelta(days=REMINDER_AFTER_DAYS - 1))
    first_sent_after = (
        _local_midnight(today) - FEEDBACK_LOOKBACK - timedelta(days=REMINDER_AFTER_DAYS)
    )
    due = EventFeedbackRequest.objects.filter(
        first_sent_at__lt=first_sent_before,
        first_sent_at__gte=first_sent_after,
        reminder_sent_at__isnull=True,
        responded_on__isnull=True,
        event__status=EventStatus.ACTIVE,
        event__event_type__in=_active_feedback_event_types(),
    ).select_related("event", "user")
    sender = get_email_sender(EmailStream.BULK)
    sent = failed = 0
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
        else:
            failed += 1
    return sent, failed
