from datetime import timedelta

from django.utils import timezone


def future_iso(days: int = 30, hours: int = 0, minutes: int = 0) -> str:
    """Use instead of hardcoded future dates, which rot and trip the check_past validator."""
    return (timezone.now() + timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


def past_iso(days: int = 1) -> str:
    """For stale/retroactive data only; normal create/edit flows reject past datetimes."""
    return (timezone.now() - timedelta(days=days)).isoformat()
