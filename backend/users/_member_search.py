from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Annotated

from community._attendance_analytics import QUALIFYING_WINDOW_DAYS, qualifying_attendance_q
from community.models import EventRSVP
from django.db import models
from django.db.models import Count, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from pydantic import BaseModel, ConfigDict, Field

from users._member_status import MemberStatus, with_member_since, with_status
from users.models import User

Days = Annotated[int | None, Field(ge=1, le=3650)]
_SIGN_IN = (
    "a sign-in is a password or login-link login; staying signed in doesn't count, so this "
    "isn't a measure of site use"
)
_QUALIFYING = (
    "qualifying = an official or club event (not community) that a host marked them attended, "
    "same as the members analytics screen"
)


class MemberSort(models.TextChoices):
    NEWEST_MEMBER = "newest_member"
    LONGEST_INACTIVE = "longest_inactive"


class MemberFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: tuple[MemberStatus, ...] = Field(
        (MemberStatus.ACTIVE, MemberStatus.STILL_ONBOARDING),
        min_length=1,
        description="statuses to include; default active and still_onboarding (everyone who can "
        "sign in); add paused for everyone not archived",
    )
    joined_within_days: Days = Field(None, description="membership started in the last n days")
    never_logged_in: bool | None = Field(
        None, description=f"true: never signed in. false: signed in at least once. {_SIGN_IN}"
    )
    not_logged_in_for_days: Days = Field(
        None,
        description="no sign-in in the last n days, counting members who never signed in; add "
        f"never_logged_in=false for only those who signed in before. {_SIGN_IN}",
    )
    inactive_for_days: Days = Field(
        None,
        description="no qualifying event starting in the last n days, counting members who never "
        f"attended one. use {QUALIFYING_WINDOW_DAYS} when asked for inactive members without a "
        f"number: that's the analytics screen's pause-candidate window. {_QUALIFYING}",
    )
    never_attended: bool | None = Field(
        None,
        description="true: never attended a qualifying event. false: attended at least one. "
        f"{_QUALIFYING}",
    )
    whatsapp_joined: bool | None = Field(None, description="has joined the whatsapp group")
    whatsapp_reminder_opt_out: bool | None = Field(
        None, description="opted out of whatsapp join reminders"
    )


def _conditions(f: MemberFilters, now: datetime) -> Iterator[Q]:
    yield Q(status__in=f.status)
    if f.joined_within_days is not None:
        yield Q(member_since__gte=now - timedelta(days=f.joined_within_days))
    if f.never_logged_in is not None:
        yield Q(last_login__isnull=f.never_logged_in)
    if f.not_logged_in_for_days is not None:
        cutoff = now - timedelta(days=f.not_logged_in_for_days)
        yield Q(last_login__isnull=True) | Q(last_login__lt=cutoff)
    if f.inactive_for_days is not None:
        cutoff = now - timedelta(days=f.inactive_for_days)
        yield Q(last_qualifying_at__isnull=True) | Q(last_qualifying_at__lt=cutoff)
    if f.never_attended is not None:
        yield Q(last_qualifying_at__isnull=f.never_attended)
    if f.whatsapp_joined is not None:
        yield Q(has_joined_whatsapp=f.whatsapp_joined)
    if f.whatsapp_reminder_opt_out is not None:
        yield Q(whatsapp_reminder_opt_out=f.whatsapp_reminder_opt_out)


def _qualifying_rsvps() -> QuerySet[EventRSVP]:
    # Correlated subqueries, not joined aggregates, so a member is still one row for count/paging.
    return EventRSVP.objects.filter(qualifying_attendance_q(), user=OuterRef("pk"))


def with_last_qualifying_at(qs: QuerySet[User]) -> QuerySet[User]:
    """Annotate last_qualifying_at: start of their latest qualifying event, null if none.

    param(qs): users to annotate
    return(QuerySet[User]): qs with a last_qualifying_at datetime
    """
    latest = _qualifying_rsvps().order_by("-event__start_datetime").values("event__start_datetime")
    return qs.annotate(last_qualifying_at=Subquery(latest[:1]))


def with_qualifying_count(qs: QuerySet[User], since: datetime) -> QuerySet[User]:
    """Annotate qualifying_count: qualifying events starting at or after since.

    param(qs): users to annotate
    param(since): window start
    return(QuerySet[User]): qs with a qualifying_count int
    """
    counted = (
        _qualifying_rsvps()
        .filter(event__start_datetime__gte=since)
        .order_by()
        .values("user")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return qs.annotate(
        qualifying_count=Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))
    )


_ORDERING = {
    MemberSort.NEWEST_MEMBER: (F("member_since").desc(), "id"),
    MemberSort.LONGEST_INACTIVE: (
        F("last_qualifying_at").asc(nulls_first=True),
        F("member_since").asc(),
        "id",
    ),
}


def members_matching(
    filters: MemberFilters, now: datetime, sort: MemberSort = MemberSort.NEWEST_MEMBER
) -> QuerySet[User]:
    """Members matching every filter, in sort order with id as the final tiebreak.

    param(filters): conditions to AND together
    param(now): reference time for the day-count filters
    param(sort): newest membership first, or never-attended then longest since a qualifying event
    return(QuerySet[User]): annotated with status, member_since and last_qualifying_at
    """
    qs = with_last_qualifying_at(with_member_since(with_status(User.objects.members())))
    return qs.filter(*_conditions(filters, now)).order_by(*_ORDERING[sort])
