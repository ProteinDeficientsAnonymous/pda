import pytest
from community.validation import Code
from django.utils import timezone
from users.models import MembershipStatus, User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def _status(user):
    user.refresh_from_db()
    if user.membership_status != MembershipStatus.ARCHIVED:
        assert user.is_member == (user.membership_status == MembershipStatus.ACTIVE_MEMBER)
    return user.membership_status


def _set_attendance_pause(api_client, headers, user, paused):
    response = api_client.patch(
        f"/api/auth/users/{user.pk}/",
        {"attendance_paused": paused},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200


def test_attendance_pause(api_client, manage_users_headers):
    member = make_user()
    _set_attendance_pause(api_client, manage_users_headers, member, True)
    assert _status(member) == MembershipStatus.ATTENDANCE_PAUSED


def test_attendance_unpause(api_client, manage_users_headers):
    paused = make_attendance_paused()
    _set_attendance_pause(api_client, manage_users_headers, paused, False)
    assert _status(paused) == MembershipStatus.ACTIVE_MEMBER


def test_archive_clears_is_member(api_client, manage_users_headers):
    member = make_user(last_login=timezone.now())
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    assert _status(member) == MembershipStatus.ARCHIVED
    assert member.is_member is False


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


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"membership_status": MembershipStatus.ACTIVE_MEMBER}, MembershipStatus.ACTIVE_MEMBER),
        ({"membership_status": MembershipStatus.PUBLIC_RSVPER}, MembershipStatus.PUBLIC_RSVPER),
        (
            {
                "membership_status": MembershipStatus.ATTENDANCE_PAUSED,
                "attendance_paused_at": timezone.now(),
            },
            MembershipStatus.ATTENDANCE_PAUSED,
        ),
        (
            {"membership_status": MembershipStatus.ARCHIVED, "archived_at": timezone.now()},
            MembershipStatus.ARCHIVED,
        ),
        (
            {"membership_status": MembershipStatus.TENTATIVE},
            MembershipStatus.TENTATIVE,
        ),
    ],
)
def test_create_user_derives_status_from_legacy_flags(fields, expected):
    assert make_user(**fields).membership_status == expected


def test_archive_records_who_archived(api_client, manage_users_user, manage_users_headers):
    member = make_user(last_login=timezone.now())
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    member.refresh_from_db()
    assert member.archived_by == manage_users_user


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
        == MembershipStatus.ACTIVE_MEMBER
    )


def test_attendance_pause_refused_while_guidelines_paused(api_client, manage_users_headers):
    member = make_user()
    _set_guidelines_pause(api_client, manage_users_headers, member, True)
    response = api_client.patch(
        f"/api/auth/users/{member.pk}/",
        {"attendance_paused": True},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 400
    assert_error_code(response, Code.User.GUIDELINES_PAUSED)


def test_guidelines_pause_replaces_attendance_pause(api_client, manage_users_headers):
    paused = make_attendance_paused()
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, paused, True)
        == MembershipStatus.GUIDELINES_PAUSED
    )
    assert paused.attendance_paused_at is None
    assert (
        _set_guidelines_pause(api_client, manage_users_headers, paused, False)
        == MembershipStatus.ACTIVE_MEMBER
    )
    assert paused.roles.filter(name="member").exists() == (
        Role.objects.filter(name="member", is_default=True).exists()
    )


def test_guidelines_paused_member_stays_in_members():
    paused = make_user(is_paused=True)
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert User.objects.members().filter(pk=paused.pk).exists()
    assert not User.objects.active_members().filter(pk=paused.pk).exists()


def test_switching_from_guidelines_to_attendance_pause(api_client, manage_users_headers):
    member = make_user()
    _set_guidelines_pause(api_client, manage_users_headers, member, True)
    response = api_client.patch(
        f"/api/auth/users/{member.pk}/",
        {"is_paused": False, "attendance_paused": True},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    assert _status(member) == MembershipStatus.ATTENDANCE_PAUSED
