import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community._event_feedback_send import send_first_requests, send_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email event feedback survey links to attendees after events, plus one reminder."

    def handle(self, *args, **options):
        now = timezone.now()
        first, first_failed = send_first_requests(now)
        reminders, reminders_failed = send_reminders(now)
        failed = first_failed + reminders_failed
        logger.info(
            "send_event_feedback_requests: sent %d request(s), %d reminder(s), %d failed",
            first,
            reminders,
            failed,
        )
        summary = f"Sent {first} feedback request(s); {reminders} reminder(s)."
        if failed:
            summary += f" {failed} failed."
        self.stdout.write(self.style.WARNING(summary) if failed else self.style.SUCCESS(summary))
