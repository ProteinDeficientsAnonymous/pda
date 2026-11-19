import pytest
from community.models import EventStatus
from tests._events import make_event
from users.models import MembershipStatus, User


def _patch(api_client, user: User, headers: dict, **payload):
    return api_client.patch(
        f"/api/auth/users/{user.pk}/", payload, content_type="application/json", **headers
    )


@pytest.mark.django_db
class TestAttendancePausePatch:
    def test_pause_applies_the_pause(self, api_client, manage_users_headers, member):
        drafted = make_event(created_by=member)

        response = _patch(api_client, member, manage_users_headers, attendance_paused=True)

        assert response.status_code == 200
        assert response.json()["attendance_paused_at"] is not None
        assert response.json()["roles"] == []
        drafted.refresh_from_db()
        assert drafted.status == EventStatus.DRAFT

    def test_unpause_is_refused(self, api_client, manage_users_headers, member):
        _patch(api_client, member, manage_users_headers, attendance_paused=True)

        response = _patch(api_client, member, manage_users_headers, attendance_paused=False)

        assert response.status_code == 400
        member.refresh_from_db()
        assert member.membership_status == MembershipStatus.ATTENDANCE_PAUSED
        assert member.attendance_paused_at is not None


@pytest.mark.django_db
class TestAttendancePausedDeletion:
    @pytest.fixture
    def paused(self, api_client, manage_users_headers, member):
        _patch(api_client, member, manage_users_headers, attendance_paused=True)
        member.refresh_from_db()
        return member

    def test_can_be_archived(self, api_client, manage_users_headers, paused):
        response = api_client.delete(f"/api/auth/users/{paused.pk}/", **manage_users_headers)

        assert response.status_code == 204
        paused.refresh_from_db()
        assert paused.archived_at is not None

    def test_can_be_hard_deleted(self, api_client, manage_users_headers, paused):
        response = api_client.delete(f"/api/auth/users/{paused.pk}/hard/", **manage_users_headers)

        assert response.status_code == 204
        assert not User.objects.filter(pk=paused.pk).exists()
