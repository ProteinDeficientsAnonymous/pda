"""Nudge event hosts to check people in right at start time. Scheduled via Railway cron every 15 minutes."""

import logging

from django.core.management.base import BaseCommand

from community._checkin_nudge import send_due_checkin_nudges

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Notify hosts + co-hosts (email + in-app) that a club/official event just started."

    def handle(self, *args, **options):
        count = send_due_checkin_nudges()
        logger.info("send_checkin_nudges: sent %d nudge(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Sent {count} check-in nudge(s)."))
