from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import connections, router
from django.utils import timezone as tz_now


class Command(BaseCommand):
    help = "Delete expired rows from the DB-backed rate-limit cache table (django_cache)."

    def handle(self, *args, **options):
        cache = caches["ratelimit"]
        db = router.db_for_write(cache.cache_model_class)
        connection = connections[db]
        table = connection.ops.quote_name(cache._table)  # noqa: SLF001

        with connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {table} WHERE {connection.ops.quote_name('expires')} < %s",  # noqa: S608
                [connection.ops.adapt_datetimefield_value(tz_now.now())],
            )
            deleted = cursor.rowcount
        self.stdout.write(f"deleted {deleted} expired cache entries")
