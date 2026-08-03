from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditLogEntry

DEFAULT_RETENTION_DAYS = 365


class Command(BaseCommand):
    help = "Delete audit log entries older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            self.stderr.write("--days must be at least 1")
            return

        cutoff = timezone.now() - timedelta(days=days)
        stale = AuditLogEntry.objects.filter(created_at__lt=cutoff)
        count = stale.count()

        if options["dry_run"]:
            self.stdout.write(f"would delete {count} entries older than {cutoff:%Y-%m-%d}")
            return

        stale.delete()
        self.stdout.write(f"deleted {count} entries older than {cutoff:%Y-%m-%d}")
