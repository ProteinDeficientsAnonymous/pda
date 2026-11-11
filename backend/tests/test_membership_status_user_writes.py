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
