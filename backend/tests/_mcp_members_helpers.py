from datetime import timedelta

from asgiref.sync import async_to_sync
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp_gateway.server import pda_mcp
from users.models import User

from tests._mcp_tool_helpers import signed_in

_phones = iter(f"+1202555{n:04d}" for n in range(2000, 3000))
BUCKETS = ("active", "still_onboarding", "paused", "archived")


def member_totals(user, **arguments):
    token = signed_in(user)
    try:
        return async_to_sync(pda_mcp.call_tool)("member_totals", arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def find_members(user, **arguments):
    token = signed_in(user)
    try:
        return async_to_sync(pda_mcp.call_tool)("find_members", arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def member_ids(user, **filters) -> set[str]:
    return {row["id"] for row in find_members(user, filters=filters)["members"]}


def ids_of(*users) -> set[str]:
    return {str(u.id) for u in users}


def make_member(**fields) -> User:
    return User.objects.create_user(phone_number=next(_phones), first_name="M", **fields)


def make_joined(days_ago: float, **fields) -> User:
    user = make_member(**fields)
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))
    return user


def make_onboarding(days_ago: float = 1, **fields) -> User:
    return make_joined(days_ago, needs_onboarding=True, **fields)


def make_onboarded(days_ago: float = 1, **fields) -> User:
    return make_joined(days_ago, onboarded_at=timezone.now(), **fields)


def make_join_request(
    user, days_ago: float, status=JoinRequestStatus.APPROVED, linked=True, phone=None
):
    return JoinRequest.objects.create(
        phone_number=phone or user.phone_number,
        email="j@e.com",
        user=user if linked else None,
        status=status,
        approved_at=timezone.now() - timedelta(days=days_ago),
    )
