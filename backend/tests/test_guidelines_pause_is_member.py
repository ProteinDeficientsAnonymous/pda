import pytest
from users.models import MembershipStatus

from tests._users import make_attendance_paused

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
