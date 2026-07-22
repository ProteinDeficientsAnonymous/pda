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


def resolve_flags() -> dict[str, bool]:
    """All known flags resolved: DB row overrides the code default if present."""
    resolved = dict(FLAG_DEFAULTS)
    overrides = FeatureFlagState.objects.filter(key__in=resolved.keys()).values_list(
        "key", "enabled"
    )
    resolved.update(overrides)
    return resolved


def flag_enabled(flag: str) -> bool:
    return resolve_flags().get(flag, False)
