"""Management command to expire stale co-host invites (issue #382).

Flips PENDING invites on already-ended events to EXPIRED. Schedule this via
Railway cron (or any scheduler) to run at least daily, e.g.:
  python manage.py expire_stale_cohost_invites
"""

import logging

from django.core.management.base import BaseCommand

from community._cohost_invite_helpers import expire_stale_cohost_invites

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expire PENDING co-host invites on events that have already ended."

    def handle(self, *args, **options):
        count = expire_stale_cohost_invites()
        logger.info("expire_stale_cohost_invites: expired %d invite(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Expired {count} invite(s)."))
