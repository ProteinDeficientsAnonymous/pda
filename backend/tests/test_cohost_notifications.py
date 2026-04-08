"""Tests for co-host added notifications."""

import json
from unittest.mock import patch

import pytest
from community.models import Event
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from notifications.service import create_cohost_added_notifications
from users.models import User

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "") -> User:
    return User.objects.create_user(phone_number=phone, password="pass", display_name=name)


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def adder(db) -> User:
    return _make_user("+12025550101", "Alice")


@pytest.fixture
def cohost(db) -> User:
    return _make_user("+12025550102", "Bob")


@pytest.fixture
def another_user(db) -> User:
    return _make_user("+12025550103", "Carol")


@pytest.fixture
def sample_event(adder) -> Event:
    return Event.objects.create(
        title="Test Event",
        start_datetime="2026-06-01T18:00:00Z",
        end_datetime="2026-06-01T20:00:00Z",
        created_by=adder,
    )


# ─── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateCohostAddedNotifications:
    def test_creates_notification_for_cohost(self, adder, cohost, sample_event):
        create_cohost_added_notifications(sample_event, [str(cohost.pk)], adder)

        notif = Notification.objects.get(recipient=cohost)
        assert notif.notification_type == NotificationType.COHOST_ADDED
        assert notif.event == sample_event
        assert "Alice" in notif.message
        assert "co-host" in notif.message
        assert "Test Event" in notif.message
        assert notif.is_read is False

    def test_skips_adder(self, adder, sample_event):
        create_cohost_added_notifications(sample_event, [str(adder.pk)], adder)
        assert Notification.objects.filter(recipient=adder).count() == 0

    def test_handles_empty_list(self, adder, sample_event):
        create_cohost_added_notifications(sample_event, [], adder)
        assert Notification.objects.count() == 0

    def test_multiple_cohosts(self, adder, cohost, another_user, sample_event):
        create_cohost_added_notifications(
            sample_event, [str(cohost.pk), str(another_user.pk)], adder
        )
        assert Notification.objects.count() == 2

    def test_skips_adder_among_multiple(self, adder, cohost, sample_event):
        create_cohost_added_notifications(sample_event, [str(adder.pk), str(cohost.pk)], adder)
        assert Notification.objects.count() == 1
        assert Notification.objects.filter(recipient=cohost).exists()

    def test_calls_notify_users(self, adder, cohost, sample_event):
        with patch("notifications.service._notify_users") as mock_notify:
            create_cohost_added_notifications(sample_event, [str(cohost.pk)], adder)
        mock_notify.assert_called_once()
        called_ids = list(mock_notify.call_args[0][0])
        assert str(cohost.pk) in called_ids
        assert str(adder.pk) not in called_ids


# ─── Integration Tests ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCohostNotificationIntegration:
    def test_create_event_with_cohost_notifies(self, api_client, adder, cohost):
        payload = {
            "title": "Cohost Party",
            "start_datetime": "2026-07-01T18:00:00Z",
            "end_datetime": "2026-07-01T20:00:00Z",
            "co_host_ids": [str(cohost.pk)],
        }
        response = api_client.post(
            "/api/community/events/",
            json.dumps(payload),
            content_type="application/json",
            **_auth_headers(adder),
        )
        assert response.status_code == 201
        assert (
            Notification.objects.filter(
                recipient=cohost, notification_type=NotificationType.COHOST_ADDED
            ).count()
            == 1
        )

    def test_create_event_does_not_notify_creator(self, api_client, adder):
        payload = {
            "title": "Solo Host",
            "start_datetime": "2026-07-01T18:00:00Z",
            "end_datetime": "2026-07-01T20:00:00Z",
            "co_host_ids": [str(adder.pk)],
        }
        api_client.post(
            "/api/community/events/",
            json.dumps(payload),
            content_type="application/json",
            **_auth_headers(adder),
        )
        assert Notification.objects.filter(recipient=adder).count() == 0

    def test_update_event_only_notifies_newly_added_cohost(
        self, api_client, adder, cohost, another_user, sample_event
    ):
        sample_event.co_hosts.set([cohost])

        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            json.dumps({"co_host_ids": [str(cohost.pk), str(another_user.pk)]}),
            content_type="application/json",
            **_auth_headers(adder),
        )
        assert response.status_code == 200
        assert (
            Notification.objects.filter(
                recipient=another_user, notification_type=NotificationType.COHOST_ADDED
            ).count()
            == 1
        )
        assert Notification.objects.filter(recipient=cohost).count() == 0

    def test_update_event_no_notification_when_cohosts_unchanged(
        self, api_client, adder, cohost, sample_event
    ):
        sample_event.co_hosts.set([cohost])

        api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            json.dumps({"co_host_ids": [str(cohost.pk)]}),
            content_type="application/json",
            **_auth_headers(adder),
        )
        assert Notification.objects.count() == 0
