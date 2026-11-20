from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from notifications.email_helpers import CheckinReminderEmailDetails, send_checkin_reminder_email
from notifications.email_sender import get_email_sender
from notifications.service import notify_checkin_reminder

from community.content.pages import DAY_OF_GUIDE_SLUG
from community.models import EditablePage, Event, EventStatus, EventType

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

NUDGE_LEAD = timedelta(hours=2)
NUDGE_GRACE = timedelta(hours=1)


def due_checkin_nudge_events(now) -> Iterable[Event]:
    return (
        Event.objects.filter(
            event_type__in=(EventType.CLUB, EventType.OFFICIAL),
            status=EventStatus.ACTIVE,
            rsvp_enabled=True,
            checkin_nudge_sent_at__isnull=True,
            start_datetime__lte=now + NUDGE_LEAD,
            start_datetime__gte=now - NUDGE_GRACE,
        )
        .select_related("created_by", "speech")
        .prefetch_related("co_hosts")
    )


def _claim_checkin_nudge(event: Event) -> bool:
    """select_for_update(skip_locked=True) serializes concurrent cron runs so exactly one claims each event."""
    with transaction.atomic():
        locked = (
            Event.objects.select_for_update(skip_locked=True)
            .filter(pk=event.pk, checkin_nudge_sent_at__isnull=True)
            .first()
        )
        if locked is None:
            return False
        locked.checkin_nudge_sent_at = timezone.now()
        locked.save(update_fields=["checkin_nudge_sent_at"])
    return True


def _speech_url(event: Event) -> str:
    if event.event_type != EventType.OFFICIAL or getattr(event, "speech", None) is not None:
        return ""
    return f"{settings.FRONTEND_BASE_URL}/events/{event.pk}/speech"


def _day_of_guide_url(event: Event) -> str:
    if event.event_type != EventType.OFFICIAL:
        return ""
    if not EditablePage.objects.filter(slug=DAY_OF_GUIDE_SLUG).exclude(content_html="").exists():
        return ""
    return f"{settings.FRONTEND_BASE_URL}/day-of"


def send_checkin_nudge(event: Event) -> bool:
    """Claim the event, then email + in-app notify the host team. Returns False if already claimed."""
    guide_url = _day_of_guide_url(event)
    if not _claim_checkin_nudge(event):
        return False

    notify_checkin_reminder(event)

    sender = get_email_sender()
    event_url = f"{settings.FRONTEND_BASE_URL}/events/{event.pk}/check-in"
    speech_url = _speech_url(event)
    for user in event.co_hosts.all():
        if not user.email:
            continue
        try:
            result = send_checkin_reminder_email(
                sender=sender,
                details=CheckinReminderEmailDetails(
                    to=user.email,
                    display_name=user.full_name or "",
                    event_title=event.title,
                    event_url=event_url,
                    speech_url=speech_url,
                    guide_url=guide_url,
                ),
            )
        except Exception:
            logger.warning("checkin_nudge_email_send_exception", exc_info=True)
            continue
        if not result.success:
            logger.warning("checkin_nudge_email_failed", extra={"error": result.error})

    return True


def send_due_checkin_nudges() -> int:
    """Send + stamp every event currently due a check-in nudge. Returns the count sent."""
    return sum(send_checkin_nudge(event) for event in due_checkin_nudge_events(timezone.now()))
