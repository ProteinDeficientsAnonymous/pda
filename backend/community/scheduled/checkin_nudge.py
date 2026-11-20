from __future__ import annotations

import logging
import re
from datetime import timedelta
from html import unescape
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from notifications.email_helpers import CheckinReminderEmailDetails, send_checkin_reminder_email
from notifications.email_sender import get_email_sender
from notifications.service import notify_checkin_reminder

from community.content.html_sanitize import sanitize_content_html
from community.content.pages import DAY_OF_GUIDE_SLUG
from community.models import EditablePage, Event, EventStatus, EventType

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

NUDGE_WINDOW = timedelta(hours=1)

_LINE_BREAK = re.compile(r"</(?:p|li)>|<br\s*/?>", re.IGNORECASE)
_SECTION_BREAK = re.compile(r"</(?:h[1-6]|blockquote|ul|ol)>", re.IGNORECASE)
_LIST_ITEM = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
_BLANK_RUNS = re.compile(r"\n{3,}")


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


def _day_of_guide_html() -> str:
    page = EditablePage.objects.filter(slug=DAY_OF_GUIDE_SLUG).only("content_html").first()
    # the django admin can write content_html directly, bypassing the save-time sanitizer
    return sanitize_content_html(page.content_html) if page and page.content_html else ""


def _plain_text(html: str) -> str:
    html = _SECTION_BREAK.sub("\n\n", _LIST_ITEM.sub("- ", html))
    text = unescape(strip_tags(_LINE_BREAK.sub("\n", html)))
    lines = "\n".join(line.strip() for line in text.splitlines())
    return _BLANK_RUNS.sub("\n\n", lines).strip()


def send_checkin_nudge(event: Event) -> bool:
    """Claim the event, then email + in-app notify the host team. Returns False if already claimed."""
    guide_html = _day_of_guide_html() if event.event_type == EventType.OFFICIAL else ""
    guide_text = _plain_text(guide_html)
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
                    guide_html=guide_html,
                    guide_text=guide_text,
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
