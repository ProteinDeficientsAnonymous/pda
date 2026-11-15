import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from notifications.email_sender import EmailSender, EmailStream, get_email_sender
from notifications.rsvp_reminder_email import RsvpReminderEmailDetails, send_rsvp_reminder_email
from users.models import PublicRsvpToken

from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from community.rsvps.public_shared import event_page_url, format_event_when, manage_rsvp_url
from community.rsvps.status_emails import member_email_ids
from community.shared import local_midnight

logger = logging.getLogger(__name__)

REMINDED_STATUSES = (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED)


def due_rsvp_reminder_events(now: datetime) -> QuerySet[Event]:
    tomorrow = local_midnight(
        timezone.localtime(now, settings.COMMUNITY_TZ).date() + timedelta(days=1)
    )
    return Event.objects.filter(
        status=EventStatus.ACTIVE,
        datetime_tbd=False,
        rsvp_reminder_sent_at__isnull=True,
        start_datetime__gte=tomorrow,
        start_datetime__lt=tomorrow + timedelta(days=1),
    )


def _rsvp_url(event: Event, rsvp: EventRSVP, member_ids: set[str]) -> str:
    if str(rsvp.user_id) in member_ids:
        return event_page_url(event)
    return manage_rsvp_url(PublicRsvpToken.issue_or_extend(rsvp.user).token)


def _send(sender: EmailSender, event: Event, rsvp: EventRSVP, member_ids: set[str]) -> bool:
    try:
        result = send_rsvp_reminder_email(
            sender=sender,
            details=RsvpReminderEmailDetails(
                to=rsvp.user.email or "",
                display_name=rsvp.user.first_name or "",
                status=rsvp.status,
                event_title=event.title,
                event_when=format_event_when(event),
                event_location=event.location,
                rsvp_url=_rsvp_url(event, rsvp, member_ids),
            ),
        )
    except Exception:  # noqa: BLE001 — one bad send must not abort the batch
        logger.warning("rsvp_reminder_email_send_exception", exc_info=True)
        return False
    if not result.success:
        logger.warning("rsvp_reminder_email_failed", extra={"error": result.error})
    return result.success


def send_rsvp_reminders_for_event(sender: EmailSender, event: Event, now: datetime) -> int:
    claimed = Event.objects.filter(pk=event.pk, rsvp_reminder_sent_at__isnull=True).update(
        rsvp_reminder_sent_at=now
    )
    if not claimed:
        return 0
    rsvps = list(
        EventRSVP.objects.filter(
            event=event,
            status__in=REMINDED_STATUSES,
            user__is_active=True,
            user__archived_at__isnull=True,
            user__email__gt="",
        ).select_related("user")
    )
    member_ids = member_email_ids([str(rsvp.user_id) for rsvp in rsvps])
    return sum(_send(sender, event, rsvp, member_ids) for rsvp in rsvps)


def send_due_rsvp_reminders(now: datetime) -> int:
    sender = get_email_sender(EmailStream.BULK)
    return sum(send_rsvp_reminders_for_event(sender, e, now) for e in due_rsvp_reminder_events(now))
