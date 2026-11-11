import pytest
from users.models import MembershipStatus

from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def test_guidelines_pausing_an_attendance_paused_member_keeps_them_listed(
    api_client, manage_users_headers
):
    paused = make_attendance_paused()
    response = api_client.patch(
        f"/api/auth/users/{paused.pk}/",
        {"is_paused": True},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    paused.refresh_from_db()
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
    assert paused.attendance_paused_at is None
    assert paused.is_member is True
    listed = api_client.get("/api/auth/users/", **manage_users_headers)
    assert str(paused.pk) in [u["id"] for u in listed.json()]


def test_lifting_a_guidelines_pause_clears_is_member(api_client, manage_users_headers):
    member = make_user(
        membership_status=MembershipStatus.GUIDELINES_PAUSED, is_paused=True, is_member=True
    )
    response = api_client.patch(
        f"/api/auth/users/{member.pk}/",
        {"is_paused": False},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.ATTENDANCE_PAUSED
    assert member.is_member is False
