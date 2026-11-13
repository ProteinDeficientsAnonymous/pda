import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.attendance.no_show_email import send_no_show_emails

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email members marked didn't go at a recent official or club event."

    def handle(self, *args, **options):
        sent, failed = send_no_show_emails(timezone.now())
        logger.info("send_no_show_emails: sent %d, %d failed", sent, failed)
        summary = f"Sent {sent} no-show email(s)."
        if failed:
            summary += f" {failed} failed."
        self.stdout.write(self.style.WARNING(summary) if failed else self.style.SUCCESS(summary))
