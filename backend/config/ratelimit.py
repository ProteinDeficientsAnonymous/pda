"""Lightweight rate-limit decorator using Django's cache framework."""

from functools import wraps

from community._validation import Code, raise_validation
from django.core.cache import cache

_PERIOD_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '10/m' into (count=10, period_seconds=60)."""
    count_str, unit = rate.split("/")
    return int(count_str), _PERIOD_MAP[unit]


def client_ip(request) -> str:
    """Extract the real client IP, honoring X-Forwarded-For for proxy setups.

    Railway / any reverse proxy hides the original client behind its own IP,
    so REMOTE_ADDR alone would collapse every caller into a single bucket.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "anon")


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
            current = cache.get(cache_key, 0)
            if current >= count:
                raise_validation(Code.Rate.LIMITED, status_code=429)
            cache.set(cache_key, current + 1, period)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
