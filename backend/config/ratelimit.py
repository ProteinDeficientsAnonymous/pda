import inspect
import ipaddress
from functools import wraps

from community.validation import Code, raise_validation
from django.core.cache import caches

_PERIOD_MAP = {"s": 1, "m": 60, "h": 3600, "d": 86400}

cache = caches["ratelimit"]


def _parse_rate(rate: str) -> tuple[int, int]:
    """Parse '10/m' into (count=10, period_seconds=60)."""
    count_str, unit = rate.split("/")
    return int(count_str), _PERIOD_MAP[unit]


# Hops our infra appends: Railway's internal proxies (100.64/10), nginx (loopback), private nets.
_INTERNAL_NETWORKS = tuple(
    ipaddress.ip_network(n)
    for n in (
        "100.64.0.0/10",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def _is_internal(hop: str) -> bool:
    try:
        addr = ipaddress.ip_address(hop)
    except ValueError:
        return False
    return any(addr in net for net in _INTERNAL_NETWORKS)


def _is_loopback(addr: str) -> bool:
    try:
        return ipaddress.ip_address(addr).is_loopback
    except ValueError:
        return False


def client_ip(request) -> str:
    """Rightmost non-internal XFF hop (the address Railway's edge saw); left of it is spoofable."""
    remote_addr = request.META.get("REMOTE_ADDR", "anon")
    # Only in-container nginx builds a trustworthy XFF; gunicorn also listens on the private network.
    if not _is_loopback(remote_addr):
        return remote_addr

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if not _is_internal(hop):
            return hop
    return remote_addr


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
            current = cache.get(cache_key, 0)
            if current >= count:
                raise_validation(Code.Rate.LIMITED, status_code=429)
            cache.set(cache_key, current + 1, period)
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
