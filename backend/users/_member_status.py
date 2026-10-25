from datetime import UTC, datetime

from django.db.models import Q

from users.models import User

# Members created before onboarded_at existed never got it set, so their resets re-flag needs_onboarding.
_ONBOARDED_AT_TRACKED_SINCE = datetime(2026, 4, 26, tzinfo=UTC)
NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True) & (
    Q(last_login__isnull=True) | Q(created_at__gte=_ONBOARDED_AT_TRACKED_SINCE)
)


def member_totals(since: datetime) -> dict[str, int]:
    """Count members by status; active, onboarding, paused and archived are disjoint.

    param(since): start of the window for new_in_period
    return(dict[str, int]): total, the four status buckets, and new_in_period
    """
    members = User.objects.members()
    live = User.objects.active_members()
    unarchived = members.filter(archived_at__isnull=True)
    return {
        "total": members.count(),
        "active": live.exclude(NOT_SET_UP).count(),
        "still_onboarding": live.filter(NOT_SET_UP).count(),
        "paused": unarchived.filter(is_paused=True).count(),
        "archived": members.filter(archived_at__isnull=False).count(),
        "new_in_period": members.filter(date_joined__gte=since).count(),
    }
