"""Lightweight rate-limit decorator using Django's cache framework."""

from functools import wraps

from community._shared import ErrorOut
from django.core.cache import cache
from ninja.responses import Status

_PERIOD_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '10/m' into (count=10, period_seconds=60)."""
    count_str, unit = rate.split("/")
    return int(count_str), _PERIOD_MAP[unit]


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
                return Status(429, ErrorOut(detail="too many requests — slow down"))
            cache.set(cache_key, current + 1, period)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
