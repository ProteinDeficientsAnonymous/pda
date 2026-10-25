from datetime import UTC, datetime

from community.models import JoinRequest, JoinRequestStatus
from django.db.models import F, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce, Greatest

from users.models import User

# Members created before onboarded_at existed never got it set, so their resets re-flag needs_onboarding.
_ONBOARDED_AT_TRACKED_SINCE = datetime(2026, 4, 26, tzinfo=UTC)
NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True) & (
    Q(last_login__isnull=True) | Q(created_at__gte=_ONBOARDED_AT_TRACKED_SINCE)
)


def with_member_since(qs: QuerySet[User]) -> QuerySet[User]:
    """Annotate member_since: their latest join-request approval, never before date_joined.

    param(qs): users to annotate
    return(QuerySet[User]): qs with a member_since datetime
    """
    # Matched by phone too: re-approving an archived member links the request by phone only.
    latest_approval = (
        JoinRequest.objects.filter(
            Q(user=OuterRef("pk")) | Q(phone_number=OuterRef("phone_number")),
            status=JoinRequestStatus.APPROVED,
            approved_at__isnull=False,
        )
        .order_by("-approved_at")
        .values("approved_at")[:1]
    )
    joined = F("date_joined")
    # Greatest is NULL on SQLite if any arg is NULL, hence the Coalesce.
    return qs.annotate(member_since=Greatest(Coalesce(Subquery(latest_approval), joined), joined))


def count_members_by_status(since: datetime) -> dict[str, int]:
    """Count members by status; the four buckets are disjoint and skip is_active=False members.

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
        "new_in_period": with_member_since(members).filter(member_since__gte=since).count(),
    }
