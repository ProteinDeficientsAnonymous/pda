from contextlib import contextmanager

from asgiref.local import Local
from django.db import models

from community.models.choices import FLAG_DEFAULTS


class FeatureFlagState(models.Model):
    """Per-flag DB override. Absence of a row means "use the code default"."""

    key = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"FeatureFlagState({self.key}={self.enabled})"


# Opt-in rather than ambient: a flag is a kill switch, so anything that caches
# it must have a bounded lifetime. Local() keeps threads and async tasks from
# sharing an entry; entering the scope again inside one reuses it.
_cache = Local()


@contextmanager
def cached_flags():
    """Serve resolve_flags() from one query for the duration of this block.

    Only for a bounded unit of work that tolerates a flag frozen for its
    lifetime — a request, not a worker loop. Nesting is safe; the outermost
    block owns the entry.
    """
    if getattr(_cache, "flags", None) is not None:
        yield
        return
    _cache.flags = resolve_flags()
    try:
        yield
    finally:
        clear_flag_cache()


def clear_flag_cache() -> None:
    """Drop any cached entry, so the next read re-queries."""
    try:
        del _cache.flags
    except AttributeError:
        pass


def resolve_flags() -> dict[str, bool]:
    """All known flags resolved: DB row overrides the code default if present.

    Cached only inside cached_flags(); uncached everywhere else, so a long-lived
    process can never hold a stale flag.
    """
    cached = getattr(_cache, "flags", None)
    if cached is not None:
        return cached
    resolved = dict(FLAG_DEFAULTS)
    overrides = FeatureFlagState.objects.filter(key__in=resolved.keys()).values_list(
        "key", "enabled"
    )
    resolved.update(overrides)
    return resolved


def flag_enabled(flag: str) -> bool:
    return resolve_flags().get(flag, False)
