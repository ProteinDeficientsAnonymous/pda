import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.planning.reminders import send_proposal_reminders, send_upcoming_notices

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remind planners about unanswered proposals and upcoming committed slots."

    def handle(self, *args, **options):
        now = timezone.now()
        reminders = send_proposal_reminders(now)
        notices = send_upcoming_notices(now)
        logger.info(
            "send_planning_reminders: sent %d proposal reminder(s), %d upcoming notice(s)",
            reminders,
            notices,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {reminders} proposal reminder(s), {notices} upcoming notice(s)."
            )
        )
