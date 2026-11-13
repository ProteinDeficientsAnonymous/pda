import logging

from django.core.management.base import BaseCommand
from notifications.email_sender import get_email_sender

from community.scheduled.rsvp_deadline_reminder import send_due_deadline_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email members still on maybe when an event's rsvp deadline is within 24 hours."

    def handle(self, *args, **options):
        count = send_due_deadline_reminders(get_email_sender())
        logger.info("send_rsvp_deadline_reminders: sent %d reminder(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Sent {count} rsvp deadline reminder(s)."))
