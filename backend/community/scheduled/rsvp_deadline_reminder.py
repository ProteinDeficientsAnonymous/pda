import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from notifications.email_helpers import format_eastern_datetime
from notifications.email_sender import EmailSender
from notifications.rsvp_deadline_email import (
    RsvpDeadlineReminderEmailDetails,
    send_rsvp_deadline_reminder_email,
)
from users.models import SIGN_IN_STATUSES, PublicRsvpToken

from community.models import EventRSVP, EventStatus, RSVPStatus

logger = logging.getLogger(__name__)

REMINDER_LEAD = timedelta(hours=24)


def due_deadline_reminders(now: datetime) -> QuerySet[EventRSVP]:
    return (
        EventRSVP.objects.filter(
            status=RSVPStatus.MAYBE,
            rsvp_deadline_reminder_sent_at__isnull=True,
            event__status=EventStatus.ACTIVE,
            event__rsvp_enabled=True,
            event__rsvp_deadline__gt=now,
            event__rsvp_deadline__lte=now + REMINDER_LEAD,
            user__is_active=True,
            user__email__isnull=False,
        )
        .exclude(user__email="")
        .select_related("event", "user")
    )


def _claim(rsvp: EventRSVP, now: datetime) -> bool:
    """The conditional update lets exactly one overlapping cron run claim each rsvp."""
    claimed = EventRSVP.objects.filter(
        pk=rsvp.pk, status=RSVPStatus.MAYBE, rsvp_deadline_reminder_sent_at__isnull=True
    ).update(rsvp_deadline_reminder_sent_at=now)
    return claimed == 1


def _rsvp_url(rsvp: EventRSVP) -> str:
    if rsvp.user.membership_status in SIGN_IN_STATUSES:
        return f"{settings.FRONTEND_BASE_URL}/events/{rsvp.event.slug or rsvp.event.pk}"
    token = PublicRsvpToken.issue_or_extend(rsvp.user)
    return f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token.token}"


def _send(sender: EmailSender, rsvp: EventRSVP, deadline: datetime) -> None:
    try:
        result = send_rsvp_deadline_reminder_email(
            sender=sender,
            details=RsvpDeadlineReminderEmailDetails(
                to=rsvp.user.email or "",
                display_name=rsvp.user.first_name,
                event_title=rsvp.event.title,
                deadline=format_eastern_datetime(deadline),
                rsvp_url=_rsvp_url(rsvp),
            ),
        )
    except Exception:  # noqa: BLE001 — one bad send must not abort the batch
        logger.warning("rsvp_deadline_reminder_send_exception", exc_info=True)
        return
    if not result.success:
        logger.warning("rsvp_deadline_reminder_failed", extra={"error": result.error})


def send_due_deadline_reminders(sender: EmailSender) -> int:
    """Email every maybe whose event's rsvp deadline is within a day, once per rsvp."""
    now = timezone.now()
    sent = 0
    for rsvp in due_deadline_reminders(now):
        deadline = rsvp.event.rsvp_deadline
        if deadline is None or not _claim(rsvp, now):
            continue
        _send(sender, rsvp, deadline)
        sent += 1
    return sent
