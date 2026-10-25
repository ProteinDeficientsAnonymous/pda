from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Annotated

from django.db.models import Q, QuerySet
from pydantic import BaseModel, ConfigDict, Field

from users._member_status import MemberStatus, with_member_since, with_status
from users.models import User

Days = Annotated[int | None, Field(ge=1, le=3650)]


class MemberFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: tuple[MemberStatus, ...] = Field(
        (MemberStatus.ACTIVE,),
        min_length=1,
        description="statuses to include; pass active, still_onboarding and paused for everyone "
        "not archived",
    )
    joined_within_days: Days = Field(None, description="membership started in the last n days")
    never_logged_in: bool | None = Field(
        None, description="true: never signed in. false: signed in at least once"
    )
    not_logged_in_for_days: Days = Field(
        None,
        description="no sign-in in the last n days, counting members who never signed in; add "
        "never_logged_in=false for only those who signed in before",
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
    if f.whatsapp_joined is not None:
        yield Q(has_joined_whatsapp=f.whatsapp_joined)
    if f.whatsapp_reminder_opt_out is not None:
        yield Q(whatsapp_reminder_opt_out=f.whatsapp_reminder_opt_out)


def find_members(filters: MemberFilters, now: datetime) -> QuerySet[User]:
    """Members matching every filter, newest membership first, id breaking ties.

    param(filters): conditions to AND together
    param(now): reference time for the day-count filters
    return(QuerySet[User]): annotated with status and member_since
    """
    qs = with_member_since(with_status(User.objects.members()))
    return qs.filter(*_conditions(filters, now)).order_by("-member_since", "id")
