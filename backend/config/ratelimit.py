import inspect
from functools import wraps

from community._validation import Code, raise_validation
from django.conf import settings
from django.core.cache import cache

_PERIOD_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '10/m' into (count=10, period_seconds=60)."""
    count_str, unit = rate.split("/")
    return int(count_str), _PERIOD_MAP[unit]


def client_ip(request) -> str:
    """Client IP for rate-limiting, resistant to X-Forwarded-For spoofing.

    Trusting XFF's leftmost value lets an attacker rotate spoofed headers into
    fresh rate-limit buckets. Instead we count back from the right: the hop at
    ``len - TRUSTED_PROXY_COUNT`` is the one the innermost trusted proxy
    observed and can't be forged. Only sound when the app is unreachable except
    via the trusted proxy chain, so TRUSTED_PROXY_COUNT must match deployment.
    """
    trusted = getattr(settings, "TRUSTED_PROXY_COUNT", 1)
    remote_addr = request.META.get("REMOTE_ADDR", "anon")

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded:
        return remote_addr

    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    # The innermost trusted proxy appended the IP it observed at this index;
    # everything to its left is attacker-controlled and ignored.
    idx = len(hops) - trusted
    if idx < 0 or idx >= len(hops):
        # XFF shorter than expected, or trusted <= 0 → can't trust a hop; use
        # REMOTE_ADDR rather than crashing or trusting attacker input.
        return remote_addr
    return hops[idx]


def auth_or_ip_key(request) -> str:
    """Rate-limit key for optional-auth endpoints: the authed user's pk when
    present, else the client IP. Use this for any endpoint that accepts both
    authenticated and anonymous callers so the two share one keying scheme."""
    pk = getattr(request.auth, "pk", None)
    return str(pk) if pk is not None else client_ip(request)


def rate_limit(*, key_func, rate: str):
    """Rate-limit decorator for Django Ninja endpoints.

    ``key_func`` may take just the request, or ``(request, **view_kwargs)`` to
    key on a path param (e.g. per-event)::

        @rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/d")
        def my_view(request, ...): ...

        @rate_limit(
            key_func=lambda r, event_id, **_: f"{r.auth.pk}:{event_id}", rate="5/h"
        )
        def my_view(request, event_id, ...): ...
    """
    count, period = _parse_rate(rate)
    wants_kwargs = _key_func_wants_kwargs(key_func)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            key = key_func(request, **kwargs) if wants_kwargs else key_func(request)
            cache_key = f"rl:{view_func.__name__}:{key}"
            # NOTE: this counter must share a cache across all workers to be
            # effective — a per-process LocMemCache lets each worker keep its
            # own count and multiplies the real limit by the worker count. See
            # the CACHES config in settings.py.
            #
            # `add` only writes (and sets the TTL) when the key is absent, so
            # the window's expiry is fixed at first hit and never reset by later
            # increments. `incr` is atomic, avoiding the read-then-write TOCTOU
            # race that allowed bursts to over-count past the limit.
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


def _key_func_wants_kwargs(key_func) -> bool:
    """True if ``key_func`` accepts more than just the request (path-param keys)."""
    try:
        params = list(inspect.signature(key_func).parameters.values())
    except (ValueError, TypeError):
        return False
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
        return True
    positional = [
        p
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) > 1
