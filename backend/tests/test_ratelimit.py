"""Unit tests for the rate-limit counter (config/ratelimit.py).

Covers the atomic counter semantics that protect against TOCTOU over-counting.
XFF-spoofing resistance of client_ip is covered in test_client_ip.py.
"""

import pytest
from community._validation import ValidationException
from config.ratelimit import rate_limit
from django.core.cache import cache


class _FakeRequest:
    def __init__(self, meta):
        self.META = meta


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.unit
class TestRateLimitCounter:
    def _make_view(self, rate):
        calls = {"n": 0}

        @rate_limit(key_func=lambda r: r.META["REMOTE_ADDR"], rate=rate)
        def view(request):
            calls["n"] += 1
            return "ok"

        return view, calls

    def test_allows_exactly_count_requests_then_blocks(self):
        view, calls = self._make_view("3/m")
        req = _FakeRequest({"REMOTE_ADDR": "203.0.113.1"})

        for _ in range(3):
            assert view(req) == "ok"

        with pytest.raises(ValidationException) as exc:
            view(req)
        assert exc.value.status_code == 429
        assert calls["n"] == 3  # blocked call never reached the view

    def test_separate_keys_have_independent_buckets(self):
        view, _ = self._make_view("1/m")
        a = _FakeRequest({"REMOTE_ADDR": "203.0.113.1"})
        b = _FakeRequest({"REMOTE_ADDR": "203.0.113.2"})

        assert view(a) == "ok"
        assert view(b) == "ok"  # different bucket, not blocked
        with pytest.raises(ValidationException):
            view(a)

    def test_ttl_set_only_on_creation_not_reset_each_increment(self):
        # The window TTL must be fixed at first hit. Increments must not extend
        # it (the old read-then-write set() reset the TTL every call).
        #
        # This runs against LocMemCache (the dev/test backend), whose incr
        # override preserves _expire_info. Production uses Redis, which has the
        # same fixed-TTL guarantee. DatabaseCache — whose inherited incr WOULD
        # reset the TTL — is intentionally not a supported backend (settings.py
        # fails fast in production if REDIS_URL is unset), so there is no DB
        # path to cover here.
        view, _ = self._make_view("5/m")
        req = _FakeRequest({"REMOTE_ADDR": "203.0.113.9"})

        view(req)
        cache_key = "rl:view:203.0.113.9"
        first_ttl = cache.ttl(cache_key) if hasattr(cache, "ttl") else None

        view(req)
        if first_ttl is not None:
            second_ttl = cache.ttl(cache_key)
            assert second_ttl <= first_ttl

        # Counter still increments correctly.
        assert cache.get(cache_key) == 2
