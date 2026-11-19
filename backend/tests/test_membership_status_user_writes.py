import pytest
from community.validation import Code
from django.utils import timezone
from users.models import MEMBER_STATUSES, MembershipStatus, User

from tests._asserts import assert_error_code
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


def test_attendance_pause(api_client, manage_users_headers):
    member = make_user()
    _set_attendance_pause(api_client, manage_users_headers, member, True)
    assert _status(member) == MembershipStatus.ATTENDANCE_PAUSED


def test_attendance_unpause_is_refused(api_client, manage_users_headers):
    paused = make_attendance_paused()
    response = api_client.patch(
        f"/api/auth/users/{paused.pk}/",
        {"attendance_paused": False},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 400
    assert _status(paused) == MembershipStatus.ATTENDANCE_PAUSED


def test_archive_clears_is_member(api_client, manage_users_headers):
    member = make_user(last_login=timezone.now())
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    assert _status(member) == MembershipStatus.ARCHIVED
    assert member.is_member is False


def _patch_guidelines_pause(api_client, headers, user, paused):
    response = api_client.patch(
        f"/api/auth/users/{user.pk}/",
        {"guidelines_paused": paused},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    return user.membership_status


def test_guidelines_pause_and_unpause(api_client, manage_users_headers):
    member = make_user(has_joined_whatsapp=True)
    assert (
        _patch_guidelines_pause(api_client, manage_users_headers, member, True)
        == MembershipStatus.GUIDELINES_PAUSED
    )
    assert member.is_member is True
    assert member.has_joined_whatsapp is False
    assert (
        _patch_guidelines_pause(api_client, manage_users_headers, member, False)
        == MembershipStatus.ATTENDANCE_PAUSED
    )
    assert member.attendance_paused_at is not None
    assert member.unpaused_at is not None


def test_attendance_pause_refused_while_guidelines_paused(api_client, manage_users_headers):
    member = make_user()
    _patch_guidelines_pause(api_client, manage_users_headers, member, True)
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
        _patch_guidelines_pause(api_client, manage_users_headers, paused, True)
        == MembershipStatus.GUIDELINES_PAUSED
    )
    assert paused.attendance_paused_at is None
    assert (
        _patch_guidelines_pause(api_client, manage_users_headers, paused, False)
        == MembershipStatus.ATTENDANCE_PAUSED
    )
    assert paused.attendance_paused_at is not None


def test_guidelines_paused_member_stays_in_members():
    paused = make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED)
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert User.objects.members().filter(pk=paused.pk).exists()
    assert not User.objects.active_members().filter(pk=paused.pk).exists()


def test_switching_from_guidelines_to_attendance_pause(api_client, manage_users_headers):
    member = make_user()
    _patch_guidelines_pause(api_client, manage_users_headers, member, True)
    response = api_client.patch(
        f"/api/auth/users/{member.pk}/",
        {"guidelines_paused": False, "attendance_paused": True},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    assert _status(member) == MembershipStatus.ATTENDANCE_PAUSED
