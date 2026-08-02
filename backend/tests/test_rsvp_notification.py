import pytest
from community.models import Event, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def host_user(db):
    return User.objects.create_user(
        phone_number="+17025550010",
        password="hostpass",
        first_name="Host",
        last_name="User",
    )


@pytest.fixture
def member_user(db):
    return User.objects.create_user(
        phone_number="+17025550011",
        password="memberpass",
        first_name="Member",
        last_name="User",
    )


@pytest.fixture
def event_with_host(db, host_user):
    return Event.objects.create(
        title="Test Event",
        description="Event for testing RSVP notifications",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        location="Test Location",
        rsvp_enabled=True,
        created_by=host_user,
    )


@pytest.mark.django_db
class TestRsvpNotifications:
    def test_rsvp_attending_notifies_host(self, api_client, member_user, event_with_host, host_user):
        refresh = RefreshToken.for_user(member_user)
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}

        response = api_client.post(
            f"/api/community/events/{event_with_host.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        notifications = Notification.objects.filter(
            recipient=host_user,
            notification_type=NotificationType.RSVP_STATUS_CHANGED,
            event=event_with_host,
            related_user=member_user,
        )
        assert notifications.exists()
        assert "is going" in notifications.first().message

    def test_rsvp_maybe_notifies_host(self, api_client, member_user, event_with_host, host_user):
        refresh = RefreshToken.for_user(member_user)
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}

        response = api_client.post(
            f"/api/community/events/{event_with_host.id}/rsvp/",
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        notifications = Notification.objects.filter(
            recipient=host_user,
            notification_type=NotificationType.RSVP_STATUS_CHANGED,
            event=event_with_host,
            related_user=member_user,
        )
        assert notifications.exists()
        assert "might go" in notifications.first().message

    def test_rsvp_cant_go_no_notification(self, api_client, member_user, event_with_host, host_user):
        refresh = RefreshToken.for_user(member_user)
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}

        response = api_client.post(
            f"/api/community/events/{event_with_host.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        notifications = Notification.objects.filter(
            recipient=host_user,
            notification_type=NotificationType.RSVP_STATUS_CHANGED,
            event=event_with_host,
        )
        assert not notifications.exists()

    def test_rsvp_host_self_rsvp_no_notification(self, api_client, event_with_host, host_user):
        refresh = RefreshToken.for_user(host_user)
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}

        response = api_client.post(
            f"/api/community/events/{event_with_host.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        notifications = Notification.objects.filter(
            recipient=host_user,
            notification_type=NotificationType.RSVP_STATUS_CHANGED,
            event=event_with_host,
        )
        assert not notifications.exists()
