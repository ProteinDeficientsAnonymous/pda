import logging

from django.core.management.base import BaseCommand

from community._cohost_reminder import send_due_cohost_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email hosts of official events starting within a week that have no co-hosts yet."

    def handle(self, *args, **options):
        count = send_due_cohost_reminders()
        logger.info("send_cohost_reminders: sent %d reminder(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Sent {count} co-host reminder(s)."))
