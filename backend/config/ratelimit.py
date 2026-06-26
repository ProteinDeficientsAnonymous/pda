"""Lightweight rate-limit decorator using Django's cache framework."""

from functools import wraps

from community._validation import Code, raise_validation
from django.core.cache import cache

_PERIOD_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}

# Number of trusted reverse-proxy hops in front of this app. Railway's edge is
# the only one today, so the real client is the 1st entry from the right of XFF.
TRUSTED_PROXY_HOPS = 1


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '10/m' into (count=10, period_seconds=60)."""
    count_str, unit = rate.split("/")
    return int(count_str), _PERIOD_MAP[unit]


def client_ip(request) -> str:
    """Extract the real client IP, honoring X-Forwarded-For for proxy setups.

    Railway / any reverse proxy hides the original client behind its own IP,
    so REMOTE_ADDR alone would collapse every caller into a single bucket.

    Security: the LEFTMOST X-Forwarded-For entry is fully client-controlled and
    therefore spoofable — a caller can prepend a fake IP to dodge rate limits.
    Only the proxies we sit behind can be trusted, and each one *appends* the
    address it saw to the right of the header. We assume exactly one trusted
    proxy hop (Railway's edge), so the real client is the RIGHTMOST entry, which
    Railway itself wrote and the client cannot forge.

    If you add additional trusted proxy layers (e.g. Cloudflare in front of
    Railway), bump TRUSTED_PROXY_HOPS so we step back past each appended hop.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            # Walk left from the end past each trusted proxy hop; clamp to the
            # leftmost entry if the chain is shorter than expected.
            index = max(0, len(hops) - TRUSTED_PROXY_HOPS)
            return hops[index]
    return request.META.get("REMOTE_ADDR", "anon")


def auth_or_ip_key(request) -> str:
    """Rate-limit key for optional-auth endpoints: the authed user's pk when
    present, else the client IP. Use this for any endpoint that accepts both
    authenticated and anonymous callers so the two share one keying scheme."""
    pk = getattr(request.auth, "pk", None)
    return str(pk) if pk is not None else client_ip(request)


def rate_limit(*, key_func, rate: str):
    """Rate-limit decorator for Django Ninja endpoints.

    Usage::

        @rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/d")
        def my_view(request, ...): ...
    """
    count, period = _parse_rate(rate)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            cache_key = f"rl:{view_func.__name__}:{key_func(request)}"
            # NOTE: this counter must share a cache across all workers to be
            # effective — a per-process LocMemCache lets each worker keep its
            # own count and multiplies the real limit by the worker count. See
            # the CACHES config in settings.py.
            #
            # `add` only writes (and sets the TTL) when the key is absent, so
            # the window's expiry is fixed at first hit and never reset by later
            # increments. `incr` is atomic, avoiding the read-then-write TOCTOU
            # race that allowed bursts to over-count past the limit.
            #
            # These guarantees hold for Redis (prod) and LocMemCache (dev/test).
            # DatabaseCache is deliberately NOT a supported backend: its
            # inherited incr is a non-atomic get-then-set that also resets the
            # TTL on every call. settings.py enforces Redis in production.
            cache.add(cache_key, 0, period)
            try:
                current = cache.incr(cache_key)
            except ValueError:
                # Key expired between add and incr; treat as a fresh window.
                cache.add(cache_key, 1, period)
                current = 1
            if current > count:
                raise_validation(Code.Rate.LIMITED, status_code=429)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
