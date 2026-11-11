import pytest
from community.models import EventRSVP
from community.validation import Code
from users.models import MembershipStatus

from tests._asserts import assert_error_code
from tests._mcp_tool_helpers import run_tool, tool_error
from tests._public_rsvp_helpers import make_official_event, post
from tests._users import make_user

pytestmark = pytest.mark.django_db

PHONE = "+14155550123"
PASSWORD = "Testpass123!"


def _patch(api_client, headers, user, body):
    return api_client.patch(
        f"/api/auth/users/{user.pk}/", body, content_type="application/json", **headers
    )


def _guidelines_paused(api_client, headers):
    member = make_user(phone_number=PHONE, email="sam@example.com", password=PASSWORD)
    assert _patch(api_client, headers, member, {"is_paused": True}).status_code == 200
    return member


def _assert_still_guidelines_paused(member):
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert member.attendance_paused_at is None


def test_both_pauses_in_one_patch_are_refused(api_client, manage_users_headers):
    member = make_user()
    response = _patch(
        api_client,
        manage_users_headers,
        member,
        {"is_paused": True, "attendance_paused": True},
    )
    assert response.status_code == 400
    assert_error_code(response, Code.User.GUIDELINES_PAUSED)
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.ACTIVE_MEMBER
    assert member.attendance_paused_at is None


def test_attendance_pause_of_a_guidelines_paused_user_is_refused(api_client, manage_users_headers):
    member = _guidelines_paused(api_client, manage_users_headers)
    response = _patch(api_client, manage_users_headers, member, {"attendance_paused": True})
    assert response.status_code == 400
    assert_error_code(response, Code.User.GUIDELINES_PAUSED)
    _assert_still_guidelines_paused(member)


def test_mcp_attendance_pause_of_a_guidelines_paused_user_is_refused(
    api_client, manage_users_user, manage_users_headers
):
    member = _guidelines_paused(api_client, manage_users_headers)
    args = {"member_id": str(member.pk), "paused": True}
    token = run_tool(manage_users_user, "set_attendance_pause", **args)["confirm_token"]
    error = tool_error(manage_users_user, "set_attendance_pause", confirm_token=token, **args)
    assert Code.User.GUIDELINES_PAUSED in error
    _assert_still_guidelines_paused(member)


def test_refused_attendance_pause_leaves_sign_in_and_public_rsvp_blocked(
    api_client, manage_users_headers
):
    member = _guidelines_paused(api_client, manage_users_headers)
    _patch(api_client, manage_users_headers, member, {"attendance_paused": True})
    login = api_client.post(
        "/api/auth/login/",
        {"phone_number": PHONE, "password": PASSWORD},
        content_type="application/json",
    )
    assert login.status_code == 403
    assert_error_code(login, Code.Auth.ACCOUNT_PAUSED)
    post(api_client, make_official_event())
    assert not EventRSVP.objects.filter(user=member).exists()
