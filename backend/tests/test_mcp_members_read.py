from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from community.models import JoinRequestStatus
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from users.models import User

from tests._mcp_members_helpers import (
    BUCKETS,
    make_join_request,
    make_joined,
    make_member,
    member_totals,
)
from tests._mcp_tool_helpers import signed_in
from tests._public_rsvp_helpers import make_non_member, make_tentative_member

pytestmark = pytest.mark.django_db


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = signed_in(test_user)
    try:
        assert "member_totals" not in {t.name for t in async_to_sync(pda_mcp.list_tools)()}
    finally:
        auth_context_var.reset(token)
    with pytest.raises(ToolError, match="permission"):
        member_totals(test_user)


def test_buckets_are_disjoint_and_match_app_definitions(manage_users_user):
    make_member()
    make_member(needs_onboarding=True)
    # A login-link reset re-flags needs_onboarding on a member who already set up.
    make_member(needs_onboarding=True, onboarded_at=timezone.now())
    make_member(is_paused=True)
    make_member(is_paused=True, needs_onboarding=True)
    make_member(archived_at=timezone.now())
    make_member(archived_at=timezone.now(), is_paused=True)
    body = member_totals(manage_users_user)
    assert {k: body[k] for k in ("total", *BUCKETS)} == {
        "total": 8,
        "active": 3,
        "still_onboarding": 1,
        "paused": 2,
        "archived": 2,
    }
    assert sum(body[k] for k in BUCKETS) == body["total"]


def test_admin_deactivated_member_is_in_no_bucket(manage_users_user):
    make_member(is_active=False)
    body = member_totals(manage_users_user)
    assert body["total"] == 2
    assert {k: body[k] for k in BUCKETS} == {
        "active": 1,
        "still_onboarding": 0,
        "paused": 0,
        "archived": 0,
    }


def test_self_deleted_member_counts_as_archived(
    api_client, auth_headers, test_user, manage_users_user
):
    body = {"password": "testpass123"}
    response = api_client.post(
        "/api/auth/me/delete/", body, content_type="application/json", **auth_headers
    )
    assert response.status_code == 204
    assert member_totals(manage_users_user)["archived"] == 1


def test_non_members_are_not_counted(manage_users_user):
    make_non_member("+12025550198", "n@e.com")
    make_tentative_member("+12025550197", "t@e.com")
    make_member(is_member=False, needs_onboarding=True)
    make_member(is_member=False, is_paused=True)
    make_member(is_member=False, archived_at=timezone.now())
    body = member_totals(manage_users_user)
    assert body["total"] == body["active"] == body["new_in_period"] == 1
    assert body["still_onboarding"] == body["paused"] == body["archived"] == 0


def test_new_in_period_boundary(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    make_joined(29.99)
    make_joined(30.01)
    make_joined(6, archived_at=timezone.now())
    make_joined(1, is_member=False)
    body = member_totals(manage_users_user)
    assert body["new_in_period"] == 2
    assert body["period_days"] == 30
    assert member_totals(manage_users_user, period_days=7)["new_in_period"] == 1
    assert member_totals(manage_users_user, period_days=365)["new_in_period"] == 3


def test_new_in_period_counts_from_membership_approval(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    promoted = make_joined(200)
    make_join_request(promoted, days_ago=200, status=JoinRequestStatus.REJECTED)
    make_join_request(promoted, days_ago=2)
    # Re-approving an archived member links the request by phone only.
    make_join_request(make_joined(300), days_ago=60)
    make_join_request(make_joined(300), days_ago=3, linked=False)
    make_join_request(make_joined(90), days_ago=1, status=JoinRequestStatus.PENDING)
    # An approval older than the account (e.g. a deleted user's phone reused) doesn't backdate it.
    make_join_request(make_joined(1), days_ago=100, linked=False)
    assert member_totals(manage_users_user)["new_in_period"] == 3


def test_linked_request_does_not_count_for_member_sharing_its_phone(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    other = make_joined(300)
    make_join_request(make_joined(300), days_ago=2, phone=other.phone_number)
    assert member_totals(manage_users_user)["new_in_period"] == 1


@pytest.mark.parametrize("period_days", [0, 366])
def test_period_days_is_bounded(manage_users_user, period_days):
    with pytest.raises(ToolError):
        member_totals(manage_users_user, period_days=period_days)
