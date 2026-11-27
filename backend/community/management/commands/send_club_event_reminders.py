import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.clubs.reminders import send_club_event_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Email club reps when a club has no event scheduled next month."

    def handle(self, *args, **options):
        sent = send_club_event_reminders(timezone.now())
        logger.info("send_club_event_reminders: sent %d email(s)", sent)
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} club event reminder(s)."))
