import asyncio
from datetime import timedelta

import pytest
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from users.models import User

from tests._public_rsvp_helpers import make_non_member, make_tentative_member
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

_phones = iter(f"+1202555{n:04d}" for n in range(2000, 3000))


def _call(user, **arguments):
    token = _signed_in(user)
    try:
        return asyncio.run(pda_mcp.call_tool("member_totals", arguments)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _member(**fields) -> User:
    return User.objects.create_user(phone_number=next(_phones), first_name="M", **fields)


def _joined(days_ago: float, **fields) -> User:
    user = _member(**fields)
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))
    return user


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = _signed_in(test_user)
    try:
        assert "member_totals" not in {t.name for t in asyncio.run(pda_mcp.list_tools())}
    finally:
        auth_context_var.reset(token)
    with pytest.raises(ToolError, match="permission"):
        _call(test_user)


def test_buckets_are_disjoint_and_match_app_definitions(manage_users_user):
    _member()
    _member(needs_onboarding=True)
    # A login-link reset re-flags needs_onboarding on a member who already set up.
    _member(needs_onboarding=True, onboarded_at=timezone.now())
    _member(is_paused=True)
    _member(is_paused=True, needs_onboarding=True)
    _member(archived_at=timezone.now())
    _member(archived_at=timezone.now(), is_paused=True)
    body = _call(manage_users_user)
    assert {k: body[k] for k in ("total", "active", "still_onboarding", "paused", "archived")} == {
        "total": 8,
        "active": 3,
        "still_onboarding": 1,
        "paused": 2,
        "archived": 2,
    }


def test_non_members_are_not_counted(manage_users_user):
    make_non_member("+12025550198", "n@e.com")
    make_tentative_member("+12025550197", "t@e.com")
    _member(is_member=False, needs_onboarding=True)
    _member(is_member=False, is_paused=True)
    _member(is_member=False, archived_at=timezone.now())
    body = _call(manage_users_user)
    assert body["total"] == body["active"] == body["new_in_period"] == 1
    assert body["still_onboarding"] == body["paused"] == body["archived"] == 0


def test_new_in_period_boundary(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    _joined(29.99)
    _joined(30.01)
    _joined(6, archived_at=timezone.now())
    _joined(1, is_member=False)
    body = _call(manage_users_user)
    assert body["new_in_period"] == 2
    assert body["period_days"] == 30
    assert _call(manage_users_user, period_days=7)["new_in_period"] == 1
    assert _call(manage_users_user, period_days=365)["new_in_period"] == 3


@pytest.mark.parametrize("period_days", [0, 366])
def test_period_days_is_bounded(manage_users_user, period_days):
    with pytest.raises(ToolError):
        _call(manage_users_user, period_days=period_days)
