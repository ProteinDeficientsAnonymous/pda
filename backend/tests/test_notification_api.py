"""Tests for the in-app notification HTTP endpoints (list/pagination, unread
count, mark-read). Service- and integration-level tests live in
test_in_app_notifications.py."""

from datetime import timedelta

import pytest
from community.models import Event
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User

from tests.conftest import future_iso

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "") -> User:
    return User.objects.create_user(phone_number=phone, password="pass", first_name=name)


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _bulk_invites(recipient: User, event: Event, count: int) -> None:
    """Create `count` invite notifications named "invite 0".."invite N-1", oldest first.

    `created_at` is `auto_now_add`, so every row in a single `bulk_create` would
    share one timestamp and have undefined ordering. We stamp distinct,
    monotonically increasing `created_at` values so "invite i" is strictly newer
    than "invite i-1" — the list endpoint orders by `-created_at`.
    """
    base = timezone.now() - timedelta(seconds=count)
    notifications = Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                notification_type=NotificationType.EVENT_INVITE,
                event=event,
                message=f"invite {i}",
            )
            for i in range(count)
        ]
    )
    for i, notification in enumerate(notifications):
        notification.created_at = base + timedelta(seconds=i)
    Notification.objects.bulk_update(notifications, ["created_at"])


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
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        created_by=inviter,
    )


# ─── List endpoint ────────────────────────────────────────────────────────────


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

    def test_defaults_to_30(self, api_client, invitee, sample_event):
        _bulk_invites(invitee, sample_event, 35)
        response = api_client.get(
            "/api/notifications/", content_type="application/json", **_auth_headers(invitee)
        )
        assert response.status_code == 200
        assert len(response.json()) == 30

    def test_honors_limit(self, api_client, invitee, sample_event):
        _bulk_invites(invitee, sample_event, 35)
        response = api_client.get(
            "/api/notifications/?limit=10",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 10
        # Newest first — invite 34 is the most recent of the 35 created.
        assert body[0]["message"] == "invite 34"

    def test_offset_pages_through_history(self, api_client, invitee, sample_event):
        _bulk_invites(invitee, sample_event, 35)
        page_one = api_client.get(
            "/api/notifications/?limit=10&offset=0",
            content_type="application/json",
            **_auth_headers(invitee),
        ).json()
        page_two = api_client.get(
            "/api/notifications/?limit=10&offset=10",
            content_type="application/json",
            **_auth_headers(invitee),
        ).json()
        assert page_one[-1]["message"] == "invite 25"
        assert page_two[0]["message"] == "invite 24"
        # No overlap between consecutive pages.
        page_one_ids = {n["id"] for n in page_one}
        assert all(n["id"] not in page_one_ids for n in page_two)

    def test_limit_above_max_is_rejected(self, api_client, invitee):
        response = api_client.get(
            "/api/notifications/?limit=51",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 422

    def test_negative_offset_is_rejected(self, api_client, invitee):
        response = api_client.get(
            "/api/notifications/?offset=-1",
            content_type="application/json",
            **_auth_headers(invitee),
        )
        assert response.status_code == 422


# ─── Unread count ─────────────────────────────────────────────────────────────


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


# ─── Mark read ────────────────────────────────────────────────────────────────


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
