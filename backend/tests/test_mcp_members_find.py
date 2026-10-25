import asyncio
from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from users.models import User

from tests._public_rsvp_helpers import make_non_member
from tests.test_mcp_members_read import _join_request, _joined, _member
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.fixture
def admin(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400), last_login=timezone.now()
    )
    return manage_users_user


def _find(user, **arguments):
    token = _signed_in(user)
    try:
        return asyncio.run(pda_mcp.call_tool("find_members", arguments)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _ids(user, **filters) -> set[str]:
    return {row["id"] for row in _find(user, filters=filters)["members"]}


def _of(*users) -> set[str]:
    return {str(u.id) for u in users}


def _logged_in(days_ago: float, **fields) -> User:
    user = _member(**fields)
    User.objects.filter(pk=user.pk).update(last_login=timezone.now() - timedelta(days=days_ago))
    return user


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = _signed_in(test_user)
    try:
        assert "find_members" not in {t.name for t in asyncio.run(pda_mcp.list_tools())}
    finally:
        auth_context_var.reset(token)
    with pytest.raises(ToolError, match="permission"):
        _find(test_user)


def test_status_defaults_to_active_and_skips_non_members(admin):
    active = _member()
    onboarding = _member(needs_onboarding=True)
    paused = _member(is_paused=True)
    archived = _member(archived_at=timezone.now())
    _member(is_active=False)
    make_non_member("+12025550198", "n@e.com")
    _member(is_member=False)
    assert _ids(admin) == _of(admin, active)
    assert _ids(admin, status=["paused", "archived"]) == _of(paused, archived)
    rows = _find(admin, filters={"status": ["active", "still_onboarding", "paused"]})["members"]
    assert {row["id"]: row["status"] for row in rows} == {
        **dict.fromkeys(_of(admin, active), "active"),
        str(onboarding.id): "still_onboarding",
        str(paused.id): "paused",
    }


def test_rows_leave_out_contact_unless_asked(admin):
    _member(email="m@e.com", has_joined_whatsapp=True, whatsapp_reminder_opt_out=True)
    row = _find(admin, filters={"whatsapp_joined": True})["members"][0]
    assert set(row) == {
        *("id", "name", "status", "member_since", "last_login"),
        *("has_joined_whatsapp", "whatsapp_reminder_opt_out"),
    }
    assert row["has_joined_whatsapp"] is row["whatsapp_reminder_opt_out"] is True
    assert datetime.fromisoformat(row["member_since"]) and row["last_login"] is None
    contact = _find(admin, filters={"whatsapp_joined": True}, include_contact=True)["members"][0]
    assert contact == {**row, "phone_number": contact["phone_number"], "email": "m@e.com"}


def test_joined_within_days_uses_membership_start(admin):
    recent = _joined(10)
    _joined(90)
    approved = _joined(300)
    _join_request(approved, days_ago=5)
    assert _ids(admin, joined_within_days=30) == _of(recent, approved)


def test_login_filters(admin):
    never = _member()
    stale = _logged_in(40)
    _logged_in(5)
    assert _ids(admin, never_logged_in=True) == _of(never)
    assert str(never.id) not in _ids(admin, never_logged_in=False)
    assert _ids(admin, not_logged_in_for_days=30) == _of(never, stale)
    assert _ids(admin, not_logged_in_for_days=30, never_logged_in=False) == _of(stale)


def test_whatsapp_filters(admin):
    User.objects.filter(pk=admin.pk).update(has_joined_whatsapp=True)
    missing = _member()
    opted_out = _member(whatsapp_reminder_opt_out=True)
    assert _ids(admin, whatsapp_joined=False) == _of(missing, opted_out)
    assert _ids(admin, whatsapp_joined=False, whatsapp_reminder_opt_out=True) == _of(opted_out)


def test_combined_filters(admin):
    match = _joined(20)
    _joined(20, has_joined_whatsapp=True)
    User.objects.filter(pk=_joined(20).pk).update(last_login=timezone.now())
    _joined(90)
    filters = {"joined_within_days": 60, "never_logged_in": True, "whatsapp_joined": False}
    assert _ids(admin, **filters) == _of(match)


def test_paging_is_stable_with_ties(admin):
    for _ in range(5):
        _member()
    User.objects.update(date_joined=timezone.now() - timedelta(days=1))
    seen, offset = [], 0
    while offset is not None:
        page = _find(admin, limit=2, offset=offset)
        assert page["total"] == 6
        seen += [row["id"] for row in page["members"]]
        offset = page["next_offset"]
    assert sorted(seen) == sorted(str(u.id) for u in User.objects.all())
