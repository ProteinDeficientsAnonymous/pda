"""Delete read notifications older than 90 days and stale SSE tickets.

SSE tickets are minted on every stream (re)connect and are single-use/short-
lived (~60s TTL), so the table accumulates dead rows fast. Anything used or
already past its expiry is safe to delete — a small grace period keeps very
recently-expired rows around so cleanup can't race a consume in flight.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification, SseTicket

_RETENTION_DAYS = 90
# Keep just-expired tickets briefly so cleanup can't race a consume in flight.
_SSE_TICKET_GRACE = timedelta(minutes=5)


class Command(BaseCommand):
    help = f"Delete read notifications older than {_RETENTION_DAYS} days and stale SSE tickets"

    def handle(self, *args, **options):
        now = timezone.now()

        notif_cutoff = now - timedelta(days=_RETENTION_DAYS)
        deleted_notifs, _ = Notification.objects.filter(
            is_read=True, created_at__lt=notif_cutoff
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_notifs} old read notifications"))

        ticket_cutoff = now - _SSE_TICKET_GRACE
        deleted_tickets, _ = SseTicket.objects.filter(
            Q(used=True) | Q(expires_at__lt=ticket_cutoff)
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_tickets} stale SSE tickets"))
