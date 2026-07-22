"""Management command to nudge event hosts to check people in right at start time.

Schedule this via Railway cron (dashboard-configured) to run every 15 minutes —
much shorter than the daily attendance-reminder cron, since this needs to fire
close to each event's start time, e.g.:
  python manage.py send_checkin_nudges
"""

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
