import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications._email_helpers import send_weekly_digest_email
from notifications.email_sender import get_email_sender
from users.models import User

from community.models import Event, EventStatus, FeatureFlag, flag_enabled

logger = logging.getLogger(__name__)


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    return (
        timezone.localtime(event.start_datetime)
        .strftime("%A, %B %d at %I:%M %p")
        .replace(" 0", " ")
    )


class Command(BaseCommand):
    help = "Email active members a digest of events starting in the next 7 days."

    def handle(self, *args, **options):
        if not flag_enabled(FeatureFlag.WEEKLY_DIGEST_EMAIL):
            return

        now = timezone.now()
        upcoming = Event.objects.filter(
            status=EventStatus.ACTIVE,
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

        calendar_url = f"{settings.FRONTEND_BASE_URL}/calendar"
        sender = get_email_sender()
        sent_count = 0

        for user in User.objects.active_members().filter(email__isnull=False).exclude(email=""):
            send_weekly_digest_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                events=events,
                calendar_url=calendar_url,
            )
            sent_count += 1

        logger.info("send_weekly_digest: sent %d digest(s)", sent_count)
        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} digest(s)."))
