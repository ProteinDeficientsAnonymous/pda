import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community._event_feedback_send import send_first_requests, send_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email event feedback survey links to attendees after events, plus one reminder."

    def handle(self, *args, **options):
        now = timezone.now()
        first = send_first_requests(now)
        reminders = send_reminders(now)
        logger.info(
            "send_event_feedback_requests: sent %d request(s), %d reminder(s)", first, reminders
        )
        self.stdout.write(
            self.style.SUCCESS(f"Sent {first} feedback request(s); {reminders} reminder(s).")
        )
