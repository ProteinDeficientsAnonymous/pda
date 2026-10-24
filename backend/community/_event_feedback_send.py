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
    from users.models import User

logger = logging.getLogger(__name__)

FEEDBACK_LOOKBACK = timedelta(days=7)


def _local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=settings.COMMUNITY_TZ)


def feedback_cutoff(now: datetime) -> datetime:
    return _local_midnight(timezone.localtime(now, settings.COMMUNITY_TZ).date())


def feedback_url(token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}/feedback/{token}"


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


def _get_or_create_request(event: Event, user: User) -> EventFeedbackRequest | None:
    try:
        with transaction.atomic():
            request, _ = EventFeedbackRequest.objects.get_or_create(
                event=event, user=user, defaults={"token": EventFeedbackRequest.new_token()}
            )
    except IntegrityError:
        return None
    return request


def _claim_first_send(request: EventFeedbackRequest, now: datetime) -> bool:
    return (
        EventFeedbackRequest.objects.filter(pk=request.pk, first_sent_at__isnull=True).update(
            first_sent_at=now
        )
        == 1
    )


def _send_first_for_event(sender: EmailSender, event: Event, now: datetime) -> int:
    rsvps = EventRSVP.objects.filter(
        event=event,
        attendance=AttendanceStatus.ATTENDED,
        user__is_active=True,
        user__archived_at__isnull=True,
    ).select_related("user")
    sent = 0
    for rsvp in rsvps:
        request = _get_or_create_request(event, rsvp.user)
        if request is None or request.first_sent_at is not None or not rsvp.user.email:
            continue
        if not _claim_first_send(request, now):
            continue
        result = _send(sender, request, reminder=False)
        if result is not None and result.success:
            sent += 1
        else:
            EventFeedbackRequest.objects.filter(pk=request.pk).update(first_sent_at=None)
    return sent


def send_first_requests(now: datetime) -> int:
    """Email a feedback link to each checked-in attendee not yet sent one, retrying failed sends. Returns emails sent."""
    sender = get_email_sender(EmailStream.BULK)
    return sum(_send_first_for_event(sender, event, now) for event in due_feedback_events(now))
