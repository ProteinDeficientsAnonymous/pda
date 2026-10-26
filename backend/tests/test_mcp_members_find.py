from datetime import datetime, timedelta

import pytest
from asgiref.sync import async_to_sync
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from mcp_gateway.tools.members_read import _page
from users._member_search import MemberFilters
from users.models import User

from tests._public_rsvp_helpers import make_non_member
from tests.test_mcp_members_read import _BUCKETS, _call, _join_request, _joined, _member
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400), last_login=timezone.now()
    )
    return manage_users_user


def _find(user, **arguments):
    token = _signed_in(user)
    try:
        return async_to_sync(pda_mcp.call_tool)("find_members", arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _ids(user, **filters) -> set[str]:
    return {row["id"] for row in _find(user, filters=filters)["members"]}


def _of(*users) -> set[str]:
    return {str(u.id) for u in users}


def _new(days_ago: float = 1, **fields) -> User:
    return _joined(days_ago, needs_onboarding=True, **fields)


def _set_up(days_ago: float = 1, **fields) -> User:
    return _joined(days_ago, onboarded_at=timezone.now(), **fields)


def _logged_in(days_ago: float, **fields) -> User:
    user = _set_up(**fields)
    User.objects.filter(pk=user.pk).update(last_login=timezone.now() - timedelta(days=days_ago))
    return user


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = _signed_in(test_user)
    try:
        assert "find_members" not in {t.name for t in async_to_sync(pda_mcp.list_tools)()}
    finally:
        auth_context_var.reset(token)
    with pytest.raises(ToolError, match="permission"):
        _find(test_user)


@pytest.mark.parametrize(
    "arguments",
    [{"filters": {"statuss": ["paused"]}}, {"filters": {"status": []}}, {"offset": 100_001}],
)
def test_bad_arguments_are_rejected(admin, arguments):
    with pytest.raises(ToolError):
        _find(admin, **arguments)


def test_status_defaults_to_live_members_and_skips_non_members(admin):
    set_up = _set_up()
    new = _new()
    paused = _new(is_paused=True)
    archived = _set_up(archived_at=timezone.now())
    _set_up(is_active=False)
    make_non_member("+12025550198", "n@e.com")
    _member(is_member=False)
    assert {row["id"]: row["status"] for row in _find(admin)["members"]} == {
        **dict.fromkeys(_of(admin, set_up), "active"),
        str(new.id): "still_onboarding",
    }
    assert _ids(admin, status=["paused", "archived"]) == _of(paused, archived)


def test_totals_match_member_totals_buckets(admin):
    _set_up()
    _new()
    _new(is_paused=True)
    _set_up(archived_at=timezone.now())
    _set_up(is_active=False)
    totals = _call(admin)
    for status in _BUCKETS:
        assert _find(admin, filters={"status": [status]})["total"] == totals[status]


def test_rows_leave_out_contact_unless_asked(admin):
    member = _new(email="m@e.com", has_joined_whatsapp=True, whatsapp_reminder_opt_out=True)
    row = _find(admin, filters={"whatsapp_joined": True})["members"][0]
    assert set(row) == {
        "id",
        "name",
        "status",
        "member_since",
        "last_login",
        "has_joined_whatsapp",
        "whatsapp_reminder_opt_out",
        "last_qualifying_at",
        "qualifying_count_12mo",
    }
    assert row["last_qualifying_at"] is None
    assert row["qualifying_count_12mo"] == 0
    assert row["has_joined_whatsapp"] is row["whatsapp_reminder_opt_out"] is True
    assert row["last_login"] is None
    assert datetime.fromisoformat(row["member_since"])
    contact = _find(admin, filters={"whatsapp_joined": True}, include_contact=True)["members"][0]
    assert contact == {**row, "phone_number": member.phone_number, "email": "m@e.com"}


def test_one_page_is_two_queries(admin, django_assert_num_queries):
    for _ in range(3):
        _new()
    with django_assert_num_queries(2):
        assert len(_page(MemberFilters(), limit=2, offset=0, include_contact=True)["members"]) == 2


def test_joined_within_days_uses_membership_start(admin):
    recent = _new(10)
    _new(90)
    approved = _set_up(300)
    _join_request(approved, days_ago=5)
    assert _ids(admin, joined_within_days=30) == _of(recent, approved)


def test_login_filters(admin):
    never = _new()
    stale = _logged_in(40)
    _logged_in(5)
    assert _ids(admin, never_logged_in=True) == _of(never)
    assert str(never.id) not in _ids(admin, never_logged_in=False)
    assert _ids(admin, not_logged_in_for_days=30) == _of(never, stale)
    assert _ids(admin, not_logged_in_for_days=30, never_logged_in=False) == _of(stale)


def test_whatsapp_filters(admin):
    User.objects.filter(pk=admin.pk).update(has_joined_whatsapp=True)
    missing = _new()
    opted_out = _new(whatsapp_reminder_opt_out=True)
    assert _ids(admin, whatsapp_joined=False) == _of(missing, opted_out)
    assert _ids(admin, whatsapp_joined=False, whatsapp_reminder_opt_out=True) == _of(opted_out)


def test_joined_recently_and_never_signed_in_finds_new_members(admin):
    # Every app-created member starts still_onboarding, so the default status must include them.
    match = _new(20)
    User.objects.filter(pk=_new(20).pk).update(last_login=timezone.now())
    _new(90)
    assert _ids(admin, joined_within_days=60, never_logged_in=True) == _of(match)


def test_paging_is_stable_with_ties(admin):
    for _ in range(5):
        _new()
    User.objects.update(date_joined=timezone.now() - timedelta(days=1))
    seen, offset = [], 0
    while offset is not None:
        page = _find(admin, limit=2, offset=offset)
        assert page["total"] == 6
        seen += [row["id"] for row in page["members"]]
        offset = page["next_offset"]
    assert sorted(seen) == sorted(str(u.id) for u in User.objects.all())
