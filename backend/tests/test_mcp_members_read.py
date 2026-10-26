from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from users.models import User

from tests._public_rsvp_helpers import make_non_member, make_tentative_member
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db

_phones = iter(f"+1202555{n:04d}" for n in range(2000, 3000))
_BUCKETS = ("active", "still_onboarding", "paused", "archived")


def _call(user, **arguments):
    token = _signed_in(user)
    try:
        return async_to_sync(pda_mcp.call_tool)("member_totals", arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _member(**fields) -> User:
    return User.objects.create_user(phone_number=next(_phones), first_name="M", **fields)


def _joined(days_ago: float, **fields) -> User:
    user = _member(**fields)
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))
    return user


def _join_request(
    user, days_ago: float, status=JoinRequestStatus.APPROVED, linked=True, phone=None
):
    return JoinRequest.objects.create(
        phone_number=phone or user.phone_number,
        email="j@e.com",
        user=user if linked else None,
        status=status,
        approved_at=timezone.now() - timedelta(days=days_ago),
    )


def test_hidden_and_forbidden_without_manage_users(test_user):
    token = _signed_in(test_user)
    try:
        assert "member_totals" not in {t.name for t in async_to_sync(pda_mcp.list_tools)()}
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
    assert {k: body[k] for k in ("total", *_BUCKETS)} == {
        "total": 8,
        "active": 3,
        "still_onboarding": 1,
        "paused": 2,
        "archived": 2,
    }
    assert sum(body[k] for k in _BUCKETS) == body["total"]


def test_admin_deactivated_member_is_in_no_bucket(manage_users_user):
    _member(is_active=False)
    body = _call(manage_users_user)
    assert body["total"] == 2
    assert {k: body[k] for k in _BUCKETS} == {
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
    assert _call(manage_users_user)["archived"] == 1


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


def test_new_in_period_counts_from_membership_approval(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    promoted = _joined(200)
    _join_request(promoted, days_ago=200, status=JoinRequestStatus.REJECTED)
    _join_request(promoted, days_ago=2)
    # Re-approving an archived member links the request by phone only.
    _join_request(_joined(300), days_ago=60)
    _join_request(_joined(300), days_ago=3, linked=False)
    _join_request(_joined(90), days_ago=1, status=JoinRequestStatus.PENDING)
    # An approval older than the account (e.g. a deleted user's phone reused) doesn't backdate it.
    _join_request(_joined(1), days_ago=100, linked=False)
    assert _call(manage_users_user)["new_in_period"] == 3


def test_linked_request_does_not_count_for_member_sharing_its_phone(manage_users_user):
    User.objects.filter(pk=manage_users_user.pk).update(
        date_joined=timezone.now() - timedelta(days=400)
    )
    other = _joined(300)
    _join_request(_joined(300), days_ago=2, phone=other.phone_number)
    assert _call(manage_users_user)["new_in_period"] == 1


@pytest.mark.parametrize("period_days", [0, 366])
def test_period_days_is_bounded(manage_users_user, period_days):
    with pytest.raises(ToolError):
        _call(manage_users_user, period_days=period_days)
