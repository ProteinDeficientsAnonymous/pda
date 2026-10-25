from datetime import timedelta
from typing import Annotated, Any

from asgiref.sync import sync_to_async
from django.utils import timezone
from pydantic import Field
from users._member_search import MemberFilters, members_matching
from users._member_status import count_members_by_status
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "count pda members by status. members only: people who just rsvp'd publicly aren't "
        "counted. total = every member. active, still_onboarding, paused and archived don't "
        "overlap and add up to total (except the rare member deactivated in the django admin): "
        "archived = account deleted, by an admin or by the member themselves; paused = paused by "
        "an admin, not archived; still_onboarding = not paused or archived but hasn't finished "
        "setting up their account yet; active = everyone else, set up and able to use the site. "
        "new_in_period = members whose membership started in the last period_days days, counted "
        "from the later of their latest join request approval and their account creation, "
        "whatever their status now, so it overlaps the other counts."
    ),
)
async def member_totals(
    period_days: Annotated[
        int, Field(ge=1, le=365, description="window for new_in_period, in days back from now")
    ] = 30,
) -> dict[str, Any]:
    since = timezone.now() - timedelta(days=period_days)
    totals = await sync_to_async(count_members_by_status)(since)
    return {**totals, "period_days": period_days, "period_start": since.isoformat()}


_ANNOTATED = ("status", "member_since")
_FIELDS = ("last_login", "has_joined_whatsapp", "whatsapp_reminder_opt_out")
_CONTACT = ("phone_number", "email")


def _row(user: User, fields: tuple[str, ...]) -> dict[str, Any]:
    values = {f: getattr(user, f) for f in (*_ANNOTATED, *fields)}
    return {"id": str(user.id), "name": user.full_name, **values}


def _page(filters: MemberFilters, limit: int, offset: int, include_contact: bool) -> dict[str, Any]:
    fields = (*_FIELDS, *_CONTACT) if include_contact else _FIELDS
    qs = members_matching(filters, timezone.now())
    total = qs.count()
    page = qs.only("first_name", "last_name", *fields)[offset : offset + limit]
    return {
        "members": [_row(u, fields) for u in page],
        "total": total,
        "next_offset": offset + limit if offset + limit < total else None,
    }


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "find pda members matching every filter given (filters combine with and), e.g. joined in "
        "the last 60 days and never signed in. statuses mean the same as in member_totals; by "
        "default only members who can sign in (active and still_onboarding) are listed. "
        "joined_within_days uses the same membership start as new_in_period. rows have id, name, "
        "status, member_since, last_login and the whatsapp flags; total is the full match count. "
        "last_login is the last password or login-link sign-in: staying signed in doesn't update "
        "it, so it isn't a measure of site use. phone and email are left out unless "
        "include_contact is true: only set it when the user explicitly asks for phone numbers or "
        "emails. paged, newest members first: fetch more with offset=next_offset."
    ),
)
async def find_members(
    filters: MemberFilters | None = None,
    include_contact: Annotated[
        bool, Field(description="add phone_number and email; only when explicitly asked for")
    ] = False,
    limit: Annotated[int, Field(ge=1, le=100, description="members per page")] = 50,
    offset: Annotated[
        int, Field(ge=0, le=100_000, description="next_offset from the previous page")
    ] = 0,
) -> dict[str, Any]:
    return await sync_to_async(_page)(filters or MemberFilters(), limit, offset, include_contact)
