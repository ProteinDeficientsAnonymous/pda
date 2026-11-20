"""Delete read notifications older than 90 days and expired SSE tickets."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone

from notifications.models import Notification, SseTicket

_RETENTION_DAYS = 90
_BATCH_SIZE = 5000


def _delete_in_batches(queryset: QuerySet) -> int:
    # Bounded deletes keep each statement short so a large backlog fits the cron timeout.
    total = 0
    while pks := list(queryset.values_list("pk", flat=True)[:_BATCH_SIZE]):
        deleted, _ = queryset.model.objects.filter(pk__in=pks).delete()
        total += deleted
    return total


class Command(BaseCommand):
    help = f"Delete read notifications older than {_RETENTION_DAYS} days and expired SSE tickets"

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=_RETENTION_DAYS)
        deleted = _delete_in_batches(
            Notification.objects.filter(is_read=True, created_at__lt=cutoff)
        )
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} old read notifications"))
        tickets = _delete_in_batches(SseTicket.objects.filter(expires_at__lt=now))
        self.stdout.write(self.style.SUCCESS(f"Deleted {tickets} expired SSE tickets"))
