import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.planning.reminders import send_proposal_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remind planners who haven't answered a planning proposal."

    def handle(self, *args, **options):
        count = send_proposal_reminders(timezone.now())
        logger.info("send_planning_reminders: sent %d proposal reminder(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Sent {count} proposal reminder(s)."))
