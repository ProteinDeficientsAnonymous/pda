import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.planning.reminders import (
    send_availability_reminders,
    send_proposal_reminders,
    send_upcoming_notices,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remind planners about unanswered proposals, upcoming slots and missing availability."

    def handle(self, *args, **options):
        now = timezone.now()
        reminders = send_proposal_reminders(now)
        notices = send_upcoming_notices(now)
        availability = send_availability_reminders(now)
        logger.info(
            "send_planning_reminders: sent %d proposal reminder(s), %d upcoming notice(s), "
            "%d availability reminder(s)",
            reminders,
            notices,
            availability,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {reminders} proposal reminder(s), {notices} upcoming notice(s), "
                f"{availability} availability reminder(s)."
            )
        )
