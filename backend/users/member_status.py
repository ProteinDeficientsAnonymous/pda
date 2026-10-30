from datetime import UTC, datetime

from community.models import JoinRequest, JoinRequestStatus
from django.db import models
from django.db.models import Case, CharField, Count, F, OuterRef, Q, QuerySet, Subquery, Value, When
from django.db.models.functions import Coalesce, Greatest

from users.models import User

# Members created before onboarded_at existed never got it set, so their resets re-flag needs_onboarding.
_ONBOARDED_AT_TRACKED_SINCE = datetime(2026, 4, 26, tzinfo=UTC)
NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True) & (
    Q(last_login__isnull=True) | Q(created_at__gte=_ONBOARDED_AT_TRACKED_SINCE)
)


class MemberStatus(models.TextChoices):
    ACTIVE = "active"
    STILL_ONBOARDING = "still_onboarding"
    PAUSED = "paused"
    ARCHIVED = "archived"


def with_status(qs: QuerySet[User]) -> QuerySet[User]:
    """Annotate status (a MemberStatus); null for a member deactivated in the django admin.

    param(qs): users to annotate
    return(QuerySet[User]): qs with a status string
    """
    status = Case(
        When(archived_at__isnull=False, then=Value(MemberStatus.ARCHIVED)),
        When(is_paused=True, then=Value(MemberStatus.PAUSED)),
        When(is_active=False, then=Value(None)),
        When(NOT_SET_UP, then=Value(MemberStatus.STILL_ONBOARDING)),
        default=Value(MemberStatus.ACTIVE),
        output_field=CharField(null=True),
    )
    return qs.annotate(status=status)


def with_member_since(qs: QuerySet[User]) -> QuerySet[User]:
    """Annotate member_since: their latest join-request approval, never before date_joined.

    param(qs): users to annotate
    return(QuerySet[User]): qs with a member_since datetime
    """
    # Unlinked requests match by phone: re-approving an archived member links by phone only.
    latest_approval = (
        JoinRequest.objects.filter(
            Q(user=OuterRef("pk")) | Q(user__isnull=True, phone_number=OuterRef("phone_number")),
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
    """Count members by status; buckets are disjoint, active/still_onboarding skip is_active=False.

    param(since): start of the window for new_in_period
    return(dict[str, int]): total, the four status buckets, and new_in_period
    """
    members = User.objects.members()
    grouped = with_status(members).values("status").annotate(n=Count("pk")).order_by()
    counts = {row["status"]: row["n"] for row in grouped}
    return {
        "total": members.count(),
        **{status.value: counts.get(status, 0) for status in MemberStatus},
        "new_in_period": with_member_since(members).filter(member_since__gte=since).count(),
    }
