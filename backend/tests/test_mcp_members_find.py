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

from tests._mcp_members_helpers import (
    BUCKETS,
    find_members,
    ids_of,
    make_join_request,
    make_member,
    make_onboarded,
    make_onboarding,
    member_ids,
    member_totals,
)
from tests._mcp_tool_helpers import signed_in
from tests._public_rsvp_helpers import make_non_member

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400), last_login=timezone.now()
    )
    return manage_users_user


def _logged_in(days_ago: float, **fields) -> User:
    user = make_onboarded(**fields)
    User.objects.filter(pk=user.pk).update(last_login=timezone.now() - timedelta(days=days_ago))
    return user


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = signed_in(test_user)
    try:
        assert "find_members" not in {t.name for t in async_to_sync(pda_mcp.list_tools)()}
    finally:
        auth_context_var.reset(token)
    with pytest.raises(ToolError, match="permission"):
        find_members(test_user)


@pytest.mark.parametrize(
    "arguments",
    [{"filters": {"statuss": ["paused"]}}, {"filters": {"status": []}}, {"offset": 100_001}],
)
def test_bad_arguments_are_rejected(admin, arguments):
    with pytest.raises(ToolError):
        find_members(admin, **arguments)


def test_status_defaults_to_live_members_and_skips_non_members(admin):
    set_up = make_onboarded()
    new = make_onboarding()
    paused = make_onboarding(is_paused=True)
    archived = make_onboarded(archived_at=timezone.now())
    make_onboarded(is_active=False)
    make_non_member("+12025550198", "n@e.com")
    make_member(is_member=False)
    assert {row["id"]: row["status"] for row in find_members(admin)["members"]} == {
        **dict.fromkeys(ids_of(admin, set_up), "active"),
        str(new.id): "still_onboarding",
    }
    assert member_ids(admin, status=["paused", "archived"]) == ids_of(paused, archived)


def test_totals_match_member_totals_buckets(admin):
    make_onboarded()
    make_onboarding()
    make_onboarding(is_paused=True)
    make_onboarded(archived_at=timezone.now())
    make_onboarded(is_active=False)
    totals = member_totals(admin)
    for status in BUCKETS:
        assert find_members(admin, filters={"status": [status]})["total"] == totals[status]


def test_rows_leave_out_contact_unless_asked(admin):
    member = make_onboarding(
        email="m@e.com", has_joined_whatsapp=True, whatsapp_reminder_opt_out=True
    )
    row = find_members(admin, filters={"whatsapp_joined": True})["members"][0]
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
    contact = find_members(admin, filters={"whatsapp_joined": True}, include_contact=True)[
        "members"
    ][0]
    assert contact == {**row, "phone_number": member.phone_number, "email": "m@e.com"}


def test_one_page_is_two_queries(admin, django_assert_num_queries):
    for _ in range(3):
        make_onboarding()
    with django_assert_num_queries(2):
        assert len(_page(MemberFilters(), limit=2, offset=0, include_contact=True)["members"]) == 2


def test_joined_within_days_uses_membership_start(admin):
    recent = make_onboarding(10)
    make_onboarding(90)
    approved = make_onboarded(300)
    make_join_request(approved, days_ago=5)
    assert member_ids(admin, joined_within_days=30) == ids_of(recent, approved)


def test_login_filters(admin):
    never = make_onboarding()
    stale = _logged_in(40)
    _logged_in(5)
    assert member_ids(admin, never_logged_in=True) == ids_of(never)
    assert str(never.id) not in member_ids(admin, never_logged_in=False)
    assert member_ids(admin, not_logged_in_for_days=30) == ids_of(never, stale)
    assert member_ids(admin, not_logged_in_for_days=30, never_logged_in=False) == ids_of(stale)


def test_whatsapp_filters(admin):
    User.objects.filter(pk=admin.pk).update(has_joined_whatsapp=True)
    missing = make_onboarding()
    opted_out = make_onboarding(whatsapp_reminder_opt_out=True)
    assert member_ids(admin, whatsapp_joined=False) == ids_of(missing, opted_out)
    assert member_ids(admin, whatsapp_joined=False, whatsapp_reminder_opt_out=True) == ids_of(
        opted_out
    )


def test_joined_recently_and_never_signed_in_finds_new_members(admin):
    # Every app-created member starts still_onboarding, so the default status must include them.
    match = make_onboarding(20)
    User.objects.filter(pk=make_onboarding(20).pk).update(last_login=timezone.now())
    make_onboarding(90)
    assert member_ids(admin, joined_within_days=60, never_logged_in=True) == ids_of(match)


def test_paging_is_stable_with_ties(admin):
    for _ in range(5):
        make_onboarding()
    User.objects.update(date_joined=timezone.now() - timedelta(days=1))
    seen, offset = [], 0
    while offset is not None:
        page = find_members(admin, limit=2, offset=offset)
        assert page["total"] == 6
        seen += [row["id"] for row in page["members"]]
        offset = page["next_offset"]
    assert sorted(seen) == sorted(str(u.id) for u in User.objects.all())
