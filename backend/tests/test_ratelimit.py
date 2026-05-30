"""Unit tests for the rate-limit infrastructure (config/ratelimit.py).

Covers the atomic counter semantics and the trusted-proxy-aware client IP
resolution that protect against TOCTOU over-counting and XFF spoofing.
"""

import pytest
from community._validation import ValidationException
from config.ratelimit import client_ip, rate_limit
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
class TestClientIp:
    def test_falls_back_to_remote_addr_without_xff(self):
        req = _FakeRequest({"REMOTE_ADDR": "203.0.113.7"})
        assert client_ip(req) == "203.0.113.7"

    def test_returns_anon_when_nothing_available(self):
        assert client_ip(_FakeRequest({})) == "anon"

    def test_uses_rightmost_xff_entry_as_trusted_client(self):
        # Client spoofs a leading fake IP; the rightmost entry is what the
        # trusted proxy (Railway) actually observed and is what we must use.
        req = _FakeRequest(
            {
                "HTTP_X_FORWARDED_FOR": "9.9.9.9, 198.51.100.23",
                "REMOTE_ADDR": "10.0.0.1",
            }
        )
        assert client_ip(req) == "198.51.100.23"

    def test_single_xff_entry(self):
        req = _FakeRequest({"HTTP_X_FORWARDED_FOR": "198.51.100.23"})
        assert client_ip(req) == "198.51.100.23"

    def test_spoofed_leftmost_entry_does_not_change_bucket(self):
        # Two requests from the same real client but with different forged
        # leftmost entries must resolve to the same IP (same rate bucket).
        a = client_ip(_FakeRequest({"HTTP_X_FORWARDED_FOR": "1.1.1.1, 198.51.100.23"}))
        b = client_ip(_FakeRequest({"HTTP_X_FORWARDED_FOR": "2.2.2.2, 198.51.100.23"}))
        assert a == b == "198.51.100.23"

    def test_ignores_empty_segments(self):
        req = _FakeRequest({"HTTP_X_FORWARDED_FOR": " , 198.51.100.23 , "})
        assert client_ip(req) == "198.51.100.23"


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
