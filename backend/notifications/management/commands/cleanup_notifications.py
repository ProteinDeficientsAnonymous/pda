"""Delete read notifications older than 90 days and expired SSE tickets."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification, SseTicket

_RETENTION_DAYS = 90


class Command(BaseCommand):
    help = f"Delete read notifications older than {_RETENTION_DAYS} days and expired SSE tickets"

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=_RETENTION_DAYS)
        deleted, _ = Notification.objects.filter(is_read=True, created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old read notifications"))
        tickets, _ = SseTicket.objects.filter(expires_at__lt=now).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {tickets} expired SSE tickets"))
