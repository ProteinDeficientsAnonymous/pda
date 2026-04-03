"""Delete read notifications older than 90 days."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification

_RETENTION_DAYS = 90


class Command(BaseCommand):
    help = f"Delete read notifications older than {_RETENTION_DAYS} days"

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=_RETENTION_DAYS)
        deleted, _ = Notification.objects.filter(is_read=True, created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old read notifications"))
