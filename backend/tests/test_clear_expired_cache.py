from io import StringIO

import pytest
from django.core.cache import caches
from django.core.management import call_command


def run() -> str:
    out = StringIO()
    call_command("clear_expired_cache", stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestClearExpiredCache:
    def test_deletes_only_expired_entries(self):
        cache = caches["ratelimit"]
        cache.set("expired", 1, timeout=-1)
        cache.set("fresh", 1, timeout=3600)

        output = run()

        assert "deleted 1 expired cache entries" in output
        assert cache.get("fresh") == 1

    def test_no_expired_entries_deletes_nothing(self):
        cache = caches["ratelimit"]
        cache.set("fresh", 1, timeout=3600)

        output = run()

        assert "deleted 0 expired cache entries" in output
        assert cache.get("fresh") == 1
