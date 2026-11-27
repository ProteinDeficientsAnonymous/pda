import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.email_sender import EmailStream, get_email_sender
from notifications.event_update_email import send_event_update_email
from users.models import HAS_EMAIL, User
from users.permissions import PermissionKey

from community.scheduled.event_update import build_event_update, is_event_update_day

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "On the 14th and the last day of the month, email members with send_event_updates "
        "the official and club event update to copy and paste, plus clubs with no events."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="print the update, send none")

    def handle(self, *args, **options):
        now = timezone.now()
        update = build_event_update(now)
        if options["dry_run"]:
            self.stdout.write(update.text)
            self.stdout.write(f"\nclubs without events: {', '.join(update.clubs_without_events)}")
            return
        if not is_event_update_day(timezone.localtime(now, settings.COMMUNITY_TZ).date()):
            self.stdout.write(self.style.SUCCESS("Not an event update day; sent 0."))
            return

        sender = get_email_sender(EmailStream.TRANSACTIONAL)
        recipients = User.objects.with_permission(PermissionKey.SEND_EVENT_UPDATES).filter(
            HAS_EMAIL, is_active=True, archived_at__isnull=True
        )
        sent = failed = 0
        for user in recipients:
            result = send_event_update_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                text=update.text,
                clubs_without_events=update.clubs_without_events,
            )
            sent, failed = (sent + 1, failed) if result.success else (sent, failed + 1)
        logger.info("send_event_updates: sent %d, %d failed", sent, failed)
        style = self.style.WARNING if failed else self.style.SUCCESS
        self.stdout.write(style(f"Sent {sent} event update(s); {failed} failed."))
