"""Tests for event flag submission and admin review endpoints."""

import pytest
from community.models import Event, EventFlag, EventFlagStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "Member") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        display_name=name,
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def member(db) -> User:
    return _make_user("+12025550101", "Alice")


@pytest.fixture
def other_member(db) -> User:
    return _make_user("+12025550102", "Bob")


@pytest.fixture
def admin_user(db) -> User:
    user = _make_user("+12025550103", "Admin")
    role = Role.objects.create(name="event_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def sample_event(db) -> Event:
    return Event.objects.create(
        title="Community Potluck",
        start_datetime="2026-06-01T18:00:00Z",
        end_datetime="2026-06-01T20:00:00Z",
        location="The Vegan Cafe",
    )


# ─── Submission ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFlagSubmission:
    def test_flag_event_success(self, api_client, member, sample_event):
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/flag/",
            {"reason": "charging money — violates guidelines"},
            content_type="application/json",
            **_auth_headers(member),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_id"] == str(sample_event.id)
        assert data["status"] == EventFlagStatus.PENDING
        assert data["reason"] == "charging money — violates guidelines"
        assert EventFlag.objects.filter(event=sample_event, flagged_by=member).exists()

    def test_flag_event_duplicate_returns_409(self, api_client, member, sample_event):
        EventFlag.objects.create(event=sample_event, flagged_by=member, reason="first flag")
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/flag/",
            {"reason": "second flag attempt"},
            content_type="application/json",
            **_auth_headers(member),
        )
        assert response.status_code == 409

    def test_flag_event_not_found_returns_404(self, api_client, member):
        import uuid

        fake_id = uuid.uuid4()
        response = api_client.post(
            f"/api/community/events/{fake_id}/flag/",
            {"reason": "some reason"},
            content_type="application/json",
            **_auth_headers(member),
        )
        assert response.status_code == 404

    def test_flag_event_unauthenticated_returns_401(self, api_client, sample_event):
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/flag/",
            {"reason": "some reason"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_flag_event_creates_admin_notification(
        self, api_client, member, admin_user, sample_event
    ):
        api_client.post(
            f"/api/community/events/{sample_event.id}/flag/",
            {"reason": "charging a fee"},
            content_type="application/json",
            **_auth_headers(member),
        )
        note = Notification.objects.filter(
            recipient=admin_user,
            notification_type=NotificationType.EVENT_FLAGGED,
            event=sample_event,
        ).first()
        assert note is not None
        assert "Community Potluck" in note.message


# ─── Admin list ───────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFlagList:
    def test_admin_can_list_flags(self, api_client, admin_user, member, sample_event):
        EventFlag.objects.create(event=sample_event, flagged_by=member, reason="bad event")
        response = api_client.get(
            "/api/community/event-flags/",
            **_auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_non_admin_cannot_list_flags(self, api_client, member, sample_event):
        response = api_client.get(
            "/api/community/event-flags/",
            **_auth_headers(member),
        )
        assert response.status_code == 403

    def test_status_filter_works(self, api_client, admin_user, member, other_member, sample_event):
        EventFlag.objects.create(
            event=sample_event,
            flagged_by=member,
            reason="pending flag",
            status=EventFlagStatus.PENDING,
        )
        EventFlag.objects.create(
            event=sample_event,
            flagged_by=other_member,
            reason="dismissed flag",
            status=EventFlagStatus.DISMISSED,
        )

        response = api_client.get(
            "/api/community/event-flags/?status=pending",
            **_auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["status"] == EventFlagStatus.PENDING


# ─── Admin review ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFlagReview:
    def test_admin_can_dismiss_flag(self, api_client, admin_user, member, sample_event):
        flag = EventFlag.objects.create(event=sample_event, flagged_by=member, reason="bogus")
        response = api_client.patch(
            f"/api/community/event-flags/{flag.id}/",
            {"status": "dismissed"},
            content_type="application/json",
            **_auth_headers(admin_user),
        )
        assert response.status_code == 200
        flag.refresh_from_db()
        assert flag.status == EventFlagStatus.DISMISSED
        assert flag.reviewed_at is not None

    def test_admin_can_action_flag(self, api_client, admin_user, member, sample_event):
        flag = EventFlag.objects.create(event=sample_event, flagged_by=member, reason="real issue")
        response = api_client.patch(
            f"/api/community/event-flags/{flag.id}/",
            {"status": "actioned"},
            content_type="application/json",
            **_auth_headers(admin_user),
        )
        assert response.status_code == 200
        flag.refresh_from_db()
        assert flag.status == EventFlagStatus.ACTIONED

    def test_invalid_status_returns_400(self, api_client, admin_user, member, sample_event):
        flag = EventFlag.objects.create(event=sample_event, flagged_by=member, reason="reason")
        response = api_client.patch(
            f"/api/community/event-flags/{flag.id}/",
            {"status": "approved"},
            content_type="application/json",
            **_auth_headers(admin_user),
        )
        assert response.status_code == 400

    def test_non_admin_cannot_review_flag(self, api_client, member, other_member, sample_event):
        flag = EventFlag.objects.create(event=sample_event, flagged_by=member, reason="reason")
        response = api_client.patch(
            f"/api/community/event-flags/{flag.id}/",
            {"status": "dismissed"},
            content_type="application/json",
            **_auth_headers(other_member),
        )
        assert response.status_code == 403
