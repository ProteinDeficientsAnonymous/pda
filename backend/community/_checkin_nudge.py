from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import CheckinReminderEmailDetails, send_checkin_reminder_email
from notifications.email_sender import get_email_sender
from notifications.service import notify_checkin_reminder

from community.models import Event, EventStatus, EventType, FeatureFlag, flag_enabled

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

NUDGE_WINDOW = timedelta(hours=1)


def due_checkin_nudge_events(now) -> Iterable[Event]:
    return Event.objects.filter(
        event_type__in=(EventType.CLUB, EventType.OFFICIAL),
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        checkin_nudge_sent_at__isnull=True,
        start_datetime__lte=now,
        start_datetime__gte=now - NUDGE_WINDOW,
    ).prefetch_related("co_hosts")


def send_checkin_nudge(event: Event) -> None:
    """Email + in-app notify the host team that check-in is open, then stamp the event sent."""
    notify_checkin_reminder(event)

    sender = get_email_sender()
    event_url = f"{settings.FRONTEND_BASE_URL}/events/{event.pk}"
    recipients = [event.created_by, *event.co_hosts.all()]
    for user in recipients:
        if user is None or not user.email:
            continue
        try:
            result = send_checkin_reminder_email(
                sender=sender,
                details=CheckinReminderEmailDetails(
                    to=user.email,
                    display_name=user.full_name or "",
                    event_title=event.title,
                    event_url=event_url,
                ),
            )
        except Exception:  # noqa: BLE001 — one bad send must not abort the batch
            logger.warning("checkin_nudge_email_send_exception", exc_info=True)
            continue
        if not result.success:
            logger.warning("checkin_nudge_email_failed", extra={"error": result.error})

    event.checkin_nudge_sent_at = timezone.now()
    event.save(update_fields=["checkin_nudge_sent_at"])


def send_due_checkin_nudges() -> int:
    """Send + stamp every event currently due a check-in nudge. Returns the count sent."""
    if not flag_enabled(FeatureFlag.HOST_ATTENDANCE_REPORT):
        return 0
    count = 0
    for event in due_checkin_nudge_events(timezone.now()):
        send_checkin_nudge(event)
        count += 1
    return count
