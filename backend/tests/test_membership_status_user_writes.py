import pytest
from users.models import MEMBER_STATUSES, MembershipStatus, User
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def _status(user):
    user.refresh_from_db()
    if user.membership_status != MembershipStatus.ARCHIVED:
        assert user.is_member == (user.membership_status in MEMBER_STATUSES)
    return user.membership_status


def _set_attendance_pause(api_client, headers, user, paused):
    response = api_client.patch(
        f"/api/auth/users/{user.pk}/",
        {"attendance_paused": paused},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200


def test_attendance_unpause(api_client, manage_users_headers):
    paused = make_attendance_paused()
    _set_attendance_pause(api_client, manage_users_headers, paused, False)
    assert _status(paused) == MembershipStatus.ACTIVE_MEMBER


@pytest.mark.parametrize(
    ("path", "payload", "permission"),
    [
        (
            "/api/auth/create-user/",
            {"phone_number": "+12025550777", "first_name": "New", "email": "new@example.com"},
            PermissionKey.CREATE_USER,
        ),
        (
            "/api/auth/bulk-create-users/",
            {"phone_numbers": ["+12025550777"]},
            PermissionKey.MANAGE_USERS,
        ),
    ],
    ids=["single", "bulk"],
)
def test_admin_created_user_is_member(api_client, path, payload, permission):
    headers = auth_headers_for(make_user(permission))
    response = api_client.post(path, payload, content_type="application/json", **headers)
    assert response.status_code in (200, 201)
    assert _status(User.objects.get(phone_number="+12025550777")) == MembershipStatus.ACTIVE_MEMBER


def _set_guidelines_pause(api_client, headers, user, paused):
    response = api_client.patch(
        f"/api/auth/users/{user.pk}/",
        {"is_paused": paused},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    return user.membership_status


def test_guidelines_pause_and_unpause(api_client, manage_users_headers):
    member = make_user()
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, member, True)
        == MembershipStatus.GUIDELINES_PAUSED
    )
    assert member.is_member is True
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, member, False)
        == MembershipStatus.ATTENDANCE_PAUSED
    )
    assert member.attendance_paused_at is not None
    assert member.unpaused_at is None


def test_guidelines_pause_replaces_attendance_pause(api_client, manage_users_headers):
    paused = make_attendance_paused()
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, paused, True)
        == MembershipStatus.GUIDELINES_PAUSED
    )
    assert paused.attendance_paused_at is None
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, paused, False)
        == MembershipStatus.ATTENDANCE_PAUSED
    )
    assert paused.attendance_paused_at is not None


def test_guidelines_paused_member_stays_in_members():
    paused = make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED)
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert User.objects.members().filter(pk=paused.pk).exists()
    assert not User.objects.active_members().filter(pk=paused.pk).exists()
