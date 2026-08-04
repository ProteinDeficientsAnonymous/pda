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


# Local(), not a module global: a cached flag must never leak across threads/tasks.
_cache = Local()
_cache_depth = Local()


@contextmanager
def cached_flags():
    """Serve resolve_flags() from one query for the duration of this block."""
    depth = getattr(_cache_depth, "value", 0)
    _cache_depth.value = depth + 1
    if depth == 0:
        _cache.flags = resolve_flags()
    try:
        yield
    finally:
        _cache_depth.value = depth
        if depth == 0:
            clear_flag_cache()


def clear_flag_cache() -> None:
    """Drop the cached entry, so the next read re-queries."""
    try:
        del _cache.flags
    except AttributeError:
        pass


def resolve_flags() -> dict[str, bool]:
    """All known flags resolved: DB row overrides the code default if present."""
    cached = getattr(_cache, "flags", None)
    if cached is not None:
        return dict(cached)
    resolved = dict(FLAG_DEFAULTS)
    overrides = FeatureFlagState.objects.filter(key__in=resolved.keys()).values_list(
        "key", "enabled"
    )
    resolved.update(overrides)
    return resolved


def flag_enabled(flag: str) -> bool:
    return resolve_flags().get(flag, False)
