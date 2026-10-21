"""Management command to permanently delete soft-deleted events older than 30 days.

Schedule this via Railway cron (or any scheduler) to run daily, e.g.:
  python manage.py purge_deleted_events
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from community.models import Event, EventStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Hard-delete events that have been soft-deleted for more than 30 days."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        qs = Event.objects.filter(status=EventStatus.DELETED, deleted_at__lt=cutoff)
        count, _ = qs.delete()
        logger.info("purge_deleted_events: permanently deleted %d event(s)", count)
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} event(s)."))
