from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from notifications.cohost_reminder_email import (
    CohostReminderEmailDetails,
    send_cohost_reminder_email,
)
from notifications.email_helpers import format_eastern_datetime
from notifications.email_sender import get_email_sender

from community.models import Event, EventStatus, EventType

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

REMINDER_LEAD = timedelta(days=7)


def due_cohost_reminder_events(now) -> Iterable[Event]:
    # co_hosts includes the creator, so a lone host means nobody else was added.
    return (
        Event.objects.filter(
            event_type=EventType.OFFICIAL,
            status=EventStatus.ACTIVE,
            cohost_reminder_sent_at__isnull=True,
            start_datetime__gt=now,
            start_datetime__lte=now + REMINDER_LEAD,
        )
        .annotate(host_count=Count("co_hosts"))
        .filter(host_count__lte=1)
        .select_related("created_by")
        .prefetch_related("co_hosts")
    )


def send_cohost_reminder(event: Event) -> bool:
    """Claim the event, then email its host. Returns False if another run already claimed it."""
    claimed = Event.objects.filter(pk=event.pk, cohost_reminder_sent_at__isnull=True).update(
        cohost_reminder_sent_at=timezone.now()
    )
    if not claimed:
        return False

    hosts = list(event.co_hosts.all()) or ([event.created_by] if event.created_by else [])
    sender = get_email_sender()
    edit_url = f"{settings.FRONTEND_BASE_URL}/events/{event.pk}/edit"
    for host in hosts:
        if not host.email:
            continue
        try:
            result = send_cohost_reminder_email(
                sender=sender,
                details=CohostReminderEmailDetails(
                    to=host.email,
                    display_name=host.first_name or "",
                    event_title=event.title,
                    event_when=format_eastern_datetime(event.start_datetime),
                    edit_url=edit_url,
                ),
            )
        except Exception:  # noqa: BLE001 — one bad send must not abort the batch
            logger.warning("cohost_reminder_email_send_exception", exc_info=True)
            continue
        if not result.success:
            logger.warning("cohost_reminder_email_failed", extra={"error": result.error})
    return True


def send_due_cohost_reminders() -> int:
    return sum(send_cohost_reminder(event) for event in due_cohost_reminder_events(timezone.now()))
