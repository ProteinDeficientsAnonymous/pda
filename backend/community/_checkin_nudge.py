from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
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
    return (
        Event.objects.filter(
            event_type__in=(EventType.CLUB, EventType.OFFICIAL),
            status=EventStatus.ACTIVE,
            rsvp_enabled=True,
            checkin_nudge_sent_at__isnull=True,
            start_datetime__lte=now,
            start_datetime__gte=now - NUDGE_WINDOW,
        )
        .select_related("created_by")
        .prefetch_related("co_hosts")
    )


def _claim_checkin_nudge(event: Event) -> bool:
    """Atomically stamp the event sent, skipping it if another run already claimed it.

    select_for_update(skip_locked=True) + the isnull re-check serialize concurrent
    cron runs so exactly one claims (and therefore sends) each event.
    Returns True if this call won the claim.
    """
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


def send_checkin_nudge(event: Event) -> bool:
    """Claim the event, then email + in-app notify the host team that check-in is open.

    Claiming before sending makes this at-most-once under overlapping cron runs.
    Returns True if this call claimed and sent the nudge (False if already claimed).
    """
    if not _claim_checkin_nudge(event):
        return False

    notify_checkin_reminder(event)

    sender = get_email_sender()
    event_url = f"{settings.FRONTEND_BASE_URL}/events/{event.pk}/attendance"
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

    return True


def send_due_checkin_nudges() -> int:
    """Send + stamp every event currently due a check-in nudge. Returns the count sent."""
    if not flag_enabled(FeatureFlag.HOST_ATTENDANCE_REPORT):
        return 0
    return sum(send_checkin_nudge(event) for event in due_checkin_nudge_events(timezone.now()))
