import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.rsvps.reminder import send_due_rsvp_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email everyone who rsvp'd to an event starting tomorrow a reminder of their rsvp."

    def handle(self, *args, **options):
        count = send_due_rsvp_reminders(timezone.now())
        logger.info("send_rsvp_reminders: sent %d reminder(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Sent {count} rsvp reminder(s)."))
