from datetime import timedelta

import pytest
from community.models import Event, EventStatus, EventType
from django.utils import timezone
from tests._auth import auth_headers_for
from users.models import User
from users.roles import Role


def _event(creator: User, event_type=EventType.COMMUNITY) -> Event:
    return Event.objects.create(
        title=f"{event_type} event",
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=3),
        created_by=creator,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
    )


def _patch(api_client, user: User, headers: dict, **payload):
    return api_client.patch(
        f"/api/auth/users/{user.pk}/", payload, content_type="application/json", **headers
    )


@pytest.mark.django_db
class TestAttendancePausePatch:
    def test_pause_applies_the_pause(self, api_client, manage_users_headers, member):
        drafted = _event(member)

        response = _patch(api_client, member, manage_users_headers, attendance_paused=True)

        assert response.status_code == 200
        assert response.json()["attendance_paused_at"] is not None
        assert response.json()["roles"] == []
        drafted.refresh_from_db()
        assert drafted.status == EventStatus.DRAFT

    def test_cannot_pause_self(self, api_client, manage_users_user, manage_users_headers):
        response = _patch(
            api_client, manage_users_user, manage_users_headers, attendance_paused=True
        )
        assert response.status_code == 400

    def test_cannot_pause_admin(self, api_client, manage_users_headers, member):
        member.roles.add(Role.objects.get_or_create(name="admin", is_default=True)[0])
        response = _patch(api_client, member, manage_users_headers, attendance_paused=True)
        assert response.status_code == 400

    def test_unpause_restores_membership_silently(
        self, api_client, manage_users_headers, member, fake_email_sender
    ):
        member_role, _ = Role.objects.get_or_create(name="member", is_default=True)
        _patch(api_client, member, manage_users_headers, attendance_paused=True)

        response = _patch(api_client, member, manage_users_headers, attendance_paused=False)

        assert response.status_code == 200
        member.refresh_from_db()
        assert member.attendance_paused_at is None
        assert member.is_member is True
        assert member.restored_at is None
        assert list(member.roles.all()) == [member_role]
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestAttendancePausedAccess:
    @pytest.fixture
    def paused(self, api_client, manage_users_headers, member):
        _patch(api_client, member, manage_users_headers, attendance_paused=True)
        member.refresh_from_db()
        return member

    @pytest.mark.parametrize(
        ("event_type", "expected"), [(EventType.OFFICIAL, 200), (EventType.COMMUNITY, 403)]
    )
    def test_rsvps_to_official_events_only(
        self, api_client, paused, other_user, event_type, expected
    ):
        event = _event(other_user, event_type)
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending"},
            content_type="application/json",
            **auth_headers_for(paused),
        )
        assert response.status_code == expected
