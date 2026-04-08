"""Tests for in-app notification system."""

from unittest.mock import patch

import pytest
from community.models import Event, PageVisibility
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from notifications.service import (
    _notify_users,
    create_event_invite_notifications,
    create_join_request_notifications,
)
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "") -> User:
    return User.objects.create_user(phone_number=phone, password="pass", display_name=name)


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def inviter(db) -> User:
    return _make_user("+12025550101", "Alice")


@pytest.fixture
def invitee(db) -> User:
    return _make_user("+12025550102", "Bob")


@pytest.fixture
def another_user(db) -> User:
    return _make_user("+12025550103", "Carol")


@pytest.fixture
def sample_event(inviter) -> Event:
    return Event.objects.create(
        title="Test Event",
        start_datetime="2026-06-01T18:00:00Z",
        end_datetime="2026-06-01T20:00:00Z",
        created_by=inviter,
    )


# ─── Service Tests ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateEventInviteNotifications:
    def test_creates_notifications_for_invitees(self, inviter, invitee, sample_event):
        create_event_invite_notifications(sample_event, [str(invitee.pk)], inviter)

        notif = Notification.objects.get(recipient=invitee)
        assert notif.notification_type == NotificationType.EVENT_INVITE
        assert notif.event == sample_event
        assert "Alice" in notif.message
        assert "Test Event" in notif.message
        assert notif.is_read is False

    def test_skips_inviter(self, inviter, sample_event):
        create_event_invite_notifications(sample_event, [str(inviter.pk)], inviter)
        assert Notification.objects.filter(recipient=inviter).count() == 0

    def test_handles_empty_list(self, inviter, sample_event):
        create_event_invite_notifications(sample_event, [], inviter)
        assert Notification.objects.count() == 0

    def test_multiple_invitees(self, inviter, invitee, another_user, sample_event):
        create_event_invite_notifications(
            sample_event, [str(invitee.pk), str(another_user.pk)], inviter
        )
        assert Notification.objects.count() == 2

    def test_skips_inviter_among_multiple(self, inviter, invitee, sample_event):
        create_event_invite_notifications(sample_event, [str(inviter.pk), str(invitee.pk)], inviter)
        assert Notification.objects.count() == 1
        assert Notification.objects.filter(recipient=invitee).exists()


# ─── API Tests ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestNotificationListAPI:
    def test_returns_own_notifications(self, api_client, inviter, invitee, sample_event):
        Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="Alice invited you to Test Event",
        )
        response = api_client.get(
            "/api/notifications/", content_type="application/json", **_auth_headers(invitee)
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["message"] == "Alice invited you to Test Event"
        assert data[0]["is_read"] is False

    def test_does_not_return_other_users_notifications(
        self, api_client, inviter, invitee, another_user, sample_event
    ):
        Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="Alice invited you to Test Event",
        )
        response = api_client.get(
            "/api/notifications/", content_type="application/json", **_auth_headers(another_user)
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_requires_auth(self, api_client):
        response = api_client.get("/api/notifications/", content_type="application/json")
        assert response.status_code == 401

    def test_limits_to_30(self, api_client, invitee, sample_event):
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient=invitee,
                    notification_type=NotificationType.EVENT_INVITE,
                    event=sample_event,
                    message=f"invite {i}",
                )
                for i in range(35)
            ]
        )
        response = api_client.get(
            "/api/notifications/", content_type="application/json", **_auth_headers(invitee)
        )
        assert response.status_code == 200
        assert len(response.json()) == 30


@pytest.mark.django_db
class TestUnreadCountAPI:
    def test_returns_unread_count(self, api_client, invitee, sample_event):
        Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="test",
            is_read=False,
        )
        Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="test read",
            is_read=True,
        )
        response = api_client.get(
            "/api/notifications/unread-count/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_returns_zero_when_none(self, api_client, invitee):
        response = api_client.get(
            "/api/notifications/unread-count/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0


@pytest.mark.django_db
class TestMarkReadAPI:
    def test_mark_one_read(self, api_client, invitee, sample_event):
        notif = Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="test",
        )
        response = api_client.post(
            f"/api/notifications/{notif.id}/read/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_other_users_notification_returns_404(
        self, api_client, invitee, another_user, sample_event
    ):
        notif = Notification.objects.create(
            recipient=invitee,
            notification_type=NotificationType.EVENT_INVITE,
            event=sample_event,
            message="test",
        )
        response = api_client.post(
            f"/api/notifications/{notif.id}/read/",
            content_type="application/json",
            **_auth_headers(another_user),
        )
        assert response.status_code == 404

    def test_mark_all_read(self, api_client, invitee, sample_event):
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient=invitee,
                    notification_type=NotificationType.EVENT_INVITE,
                    event=sample_event,
                    message=f"test {i}",
                )
                for i in range(3)
            ]
        )
        response = api_client.post(
            "/api/notifications/read-all/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        assert Notification.objects.filter(recipient=invitee, is_read=False).count() == 0


# ─── Integration Tests ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEventInviteIntegration:
    def test_create_event_with_invites_creates_notifications(self, api_client, inviter, invitee):
        payload = {
            "title": "Party",
            "start_datetime": "2026-07-01T18:00:00Z",
            "end_datetime": "2026-07-01T20:00:00Z",
            "invited_user_ids": [str(invitee.pk)],
        }
        response = api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **_auth_headers(inviter),
        )
        assert response.status_code == 201
        assert Notification.objects.filter(recipient=invitee).count() == 1

    def test_create_event_inviter_not_notified(self, api_client, inviter):
        payload = {
            "title": "Solo",
            "start_datetime": "2026-07-01T18:00:00Z",
            "end_datetime": "2026-07-01T20:00:00Z",
            "invited_user_ids": [str(inviter.pk)],
        }
        api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **_auth_headers(inviter),
        )
        assert Notification.objects.filter(recipient=inviter).count() == 0

    def test_update_event_only_notifies_newly_invited(
        self, api_client, inviter, invitee, another_user, sample_event
    ):
        # Pre-invite invitee
        sample_event.invited_users.set([invitee])

        # Update to also add another_user
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"invited_user_ids": [str(invitee.pk), str(another_user.pk)]},
            content_type="application/json",
            **_auth_headers(inviter),
        )
        assert response.status_code == 200
        # Only another_user should get a notification (invitee was already invited)
        assert Notification.objects.filter(recipient=another_user).count() == 1
        assert Notification.objects.filter(recipient=invitee).count() == 0


# ─── Visibility Tests ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCanSeeInvited:
    def test_invited_user_can_see_invited_list_on_invite_only_event(
        self, api_client, inviter, invitee
    ):
        event = Event.objects.create(
            title="Invite-only party",
            start_datetime="2026-06-01T18:00:00Z",
            end_datetime="2026-06-01T20:00:00Z",
            created_by=inviter,
            visibility=PageVisibility.INVITE_ONLY,
        )
        event.invited_users.set([invitee])

        response = api_client.get(
            f"/api/community/events/{event.id}/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        data = response.json()
        assert str(invitee.pk) in data["invited_user_ids"]

    def test_invited_user_cannot_see_invited_list_on_public_event(
        self, api_client, inviter, invitee
    ):
        event = Event.objects.create(
            title="Public with invites",
            start_datetime="2026-06-01T18:00:00Z",
            end_datetime="2026-06-01T20:00:00Z",
            created_by=inviter,
            visibility=PageVisibility.PUBLIC,
        )
        event.invited_users.set([invitee])

        response = api_client.get(
            f"/api/community/events/{event.id}/",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        assert response.json()["invited_user_ids"] == []

    def test_non_invited_user_cannot_see_invited_list(
        self, api_client, inviter, invitee, another_user
    ):
        event = Event.objects.create(
            title="Invite-only party",
            start_datetime="2026-06-01T18:00:00Z",
            end_datetime="2026-06-01T20:00:00Z",
            created_by=inviter,
            visibility=PageVisibility.INVITE_ONLY,
        )
        event.invited_users.set([invitee])

        response = api_client.get(
            f"/api/community/events/{event.id}/",
            content_type="application/json",
            **_auth_headers(another_user),
        )
        assert response.status_code == 404


# ─── Join Request Notification Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestCreateJoinRequestNotifications:
    def _make_user_with_permission(self, phone: str, permission: str) -> User:
        user = _make_user(phone)
        role = Role.objects.create(name=f"role_{phone}", permissions=[permission])
        user.roles.add(role)
        return user

    def test_notifies_user_with_approve_permission(self, db):
        user = self._make_user_with_permission("+12025550201", PermissionKey.APPROVE_JOIN_REQUESTS)
        create_join_request_notifications("Sprout")
        notif = Notification.objects.get(recipient=user)
        assert notif.notification_type == NotificationType.JOIN_REQUEST
        assert notif.event is None
        assert notif.is_read is False
        assert "Sprout" in notif.message

    def test_notifies_admin_role_user(self, db):
        user = _make_user("+12025550202")
        admin_role = Role.objects.get(name="admin", is_default=True)
        user.roles.add(admin_role)
        create_join_request_notifications("Sprout")
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_no_notification_for_unpermissioned_user(self, db):
        user = _make_user("+12025550203")
        create_join_request_notifications("Sprout")
        assert Notification.objects.filter(recipient=user).count() == 0

    def test_no_duplicate_for_user_with_admin_and_explicit_permission(self, db):
        user = _make_user("+12025550204")
        admin_role = Role.objects.get(name="admin", is_default=True)
        extra_role = Role.objects.create(
            name="also_approver",
            permissions=[PermissionKey.APPROVE_JOIN_REQUESTS],
        )
        user.roles.add(admin_role, extra_role)
        create_join_request_notifications("Sprout")
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_message_contains_display_name(self, db):
        self._make_user_with_permission("+12025550205", PermissionKey.APPROVE_JOIN_REQUESTS)
        create_join_request_notifications("Luna Green")
        notif = Notification.objects.first()
        assert "Luna Green" in notif.message

    def test_no_error_when_no_recipients(self, db):
        create_join_request_notifications("Sprout")
        assert Notification.objects.count() == 0


@pytest.mark.django_db
class TestPgNotifyIntegration:
    """Verify that _notify_users is called when notifications are created."""

    def test_event_invite_calls_notify_users(self, inviter, invitee, sample_event):
        with patch("notifications.service._notify_users") as mock_notify:
            create_event_invite_notifications(sample_event, [str(invitee.pk)], inviter)
        mock_notify.assert_called_once()
        called_ids = list(mock_notify.call_args[0][0])
        assert str(invitee.pk) in called_ids

    def test_event_invite_excludes_inviter_from_notify(self, inviter, invitee, sample_event):
        with patch("notifications.service._notify_users") as mock_notify:
            create_event_invite_notifications(
                sample_event, [str(inviter.pk), str(invitee.pk)], inviter
            )
        called_ids = list(mock_notify.call_args[0][0])
        assert str(inviter.pk) not in called_ids
        assert str(invitee.pk) in called_ids

    def test_join_request_calls_notify_users(self, db):
        user = _make_user("+12025550301")
        admin_role = Role.objects.get(name="admin", is_default=True)
        user.roles.add(admin_role)
        with patch("notifications.service._notify_users") as mock_notify:
            create_join_request_notifications("Sprout")
        mock_notify.assert_called_once()
        called_ids = list(mock_notify.call_args[0][0])
        assert str(user.pk) in called_ids

    def test_notify_users_skips_on_non_postgresql(self, db):
        """_notify_users is a no-op when not on PostgreSQL (e.g. SQLite in tests)."""
        # Should not raise even though no pg_notify is available
        _notify_users(["fake-uuid"])
