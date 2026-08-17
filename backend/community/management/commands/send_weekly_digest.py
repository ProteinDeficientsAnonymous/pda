import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications._email_helpers import format_eastern_datetime, send_weekly_digest_email
from notifications.email_sender import EmailStream, get_email_sender
from users.models import User

from community.models import Event, EventStatus, EventType

logger = logging.getLogger(__name__)


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    return format_eastern_datetime(event.start_datetime)


class Command(BaseCommand):
    help = "Email active members a digest of events starting in the next 7 days."

    def handle(self, *args, **options):
        now = timezone.now()
        upcoming = Event.objects.filter(
            status=EventStatus.ACTIVE,
            event_type__in=(EventType.OFFICIAL, EventType.CLUB),
            deleted_at__isnull=True,
            start_datetime__gte=now,
            start_datetime__lt=now + timedelta(days=7),
        ).order_by("start_datetime")

        events = [
            {
                "title": event.title,
                "when": _format_event_when(event),
                "location": event.location,
                "url": f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.pk}",
            }
            for event in upcoming
        ]
        if not events:
            logger.info("send_weekly_digest: no upcoming events, skipped")
            self.stdout.write(self.style.SUCCESS("No upcoming events; sent 0 digest(s)."))
            return

        urls = {
            "calendar_url": f"{settings.FRONTEND_BASE_URL}/calendar",
            "settings_url": f"{settings.FRONTEND_BASE_URL}/settings",
        }
        sender = get_email_sender(EmailStream.BULK)
        sent_count = 0
        failed_count = 0

        recipients = (
            User.objects.active_members()
            .filter(email__isnull=False, weekly_digest_opt_out=False)
            .exclude(email="")
        )
        for user in recipients:
            result = send_weekly_digest_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                events=events,
                urls=urls,
            )
            if result.success:
                sent_count += 1
            else:
                failed_count += 1

        logger.info("send_weekly_digest: sent %d digest(s), %d failed", sent_count, failed_count)
        summary = f"Sent {sent_count} digest(s); {failed_count} failed."
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(summary))
