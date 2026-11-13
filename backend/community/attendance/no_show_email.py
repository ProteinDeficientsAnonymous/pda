from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from notifications.email_sender import get_email_sender
from notifications.no_show_email import send_no_show_email

from community.event_feedback.send import event_date_label, feedback_cutoff
from community.models import AttendanceStatus, EventRSVP, EventStatus, EventType
from community.models.event import is_past_q

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from notifications.email_sender import EmailSender

logger = logging.getLogger(__name__)

NO_SHOW_LOOKBACK = timedelta(days=7)


def due_no_show_rsvps(now: datetime) -> QuerySet[EventRSVP]:
    cutoff = feedback_cutoff(now)
    return EventRSVP.objects.filter(
        is_past_q(cutoff, prefix="event__"),
        ~is_past_q(cutoff - NO_SHOW_LOOKBACK, prefix="event__"),
        event__status=EventStatus.ACTIVE,
        event__event_type__in=(EventType.OFFICIAL, EventType.CLUB),
        attendance=AttendanceStatus.DIDNT_GO,
        no_show_emailed_at__isnull=True,
        user__is_active=True,
        user__archived_at__isnull=True,
    ).select_related("event", "user")


def _claim(rsvp: EventRSVP, now: datetime) -> bool:
    return (
        EventRSVP.objects.filter(pk=rsvp.pk, no_show_emailed_at__isnull=True).update(
            no_show_emailed_at=now
        )
        == 1
    )


def _send(sender: EmailSender, rsvp: EventRSVP, calendar_url: str) -> bool:
    try:
        result = send_no_show_email(
            sender=sender,
            to=rsvp.user.email or "",
            display_name=rsvp.user.first_name or "",
            event_title=rsvp.event.title,
            event_date=event_date_label(rsvp.event),
            calendar_url=calendar_url,
        )
    except Exception:  # noqa: BLE001 — one bad send must not abort the batch
        logger.warning("no_show_email_send_exception", exc_info=True)
        return False
    if not result.success:
        logger.warning("no_show_email_failed", extra={"error": result.error})
    return result.success


def send_no_show_emails(now: datetime) -> tuple[int, int]:
    """Email each member marked didn't go at a recent official or club event, once per RSVP. Returns (sent, failed)."""
    sender = get_email_sender()
    calendar_url = f"{settings.FRONTEND_BASE_URL}/calendar"
    sent = failed = 0
    for rsvp in due_no_show_rsvps(now):
        if not rsvp.user.email or not _claim(rsvp, now):
            continue
        if _send(sender, rsvp, calendar_url):
            sent += 1
        else:
            failed += 1
            EventRSVP.objects.filter(pk=rsvp.pk).update(no_show_emailed_at=None)
    return sent, failed
