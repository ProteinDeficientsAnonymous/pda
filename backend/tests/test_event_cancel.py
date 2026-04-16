"""Tests for event cancel/uncancel/delete status transitions via PATCH."""

import pytest
from community.models import Event, EventStatus
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_events_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+14155551235",
        password="eventmanagerpass123",
        display_name="Event Manager 2",
    )
    role = Role.objects.create(
        name="event_manager_cancel", permissions=[PermissionKey.MANAGE_EVENTS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_events_headers(manage_events_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_events_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def upcoming_event_with_rsvp(db, manage_events_user, test_user):
    """An upcoming event with an attending RSVP — can be cancelled."""
    from community.models import EventRSVP, RSVPStatus

    event = Event.objects.create(
        title="Cancellable Event",
        description="Has attendees",
        start_datetime="2027-04-01T18:00:00Z",
        end_datetime="2027-04-01T20:00:00Z",
        location="The Vegan Cafe",
        created_by=manage_events_user,
        rsvp_enabled=True,
    )
    EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
    return event


@pytest.fixture
def upcoming_event_no_attendees(db, manage_events_user):
    """An upcoming event with no invites/RSVPs — must be deleted, not cancelled."""
    return Event.objects.create(
        title="Empty Event",
        description="No one invited",
        start_datetime="2027-04-01T18:00:00Z",
        end_datetime="2027-04-01T20:00:00Z",
        location="The Vegan Cafe",
        created_by=manage_events_user,
    )


@pytest.fixture
def past_event(db, manage_events_user):
    return Event.objects.create(
        title="Past Event",
        description="Already happened",
        start_datetime="2020-01-01T18:00:00Z",
        end_datetime="2020-01-01T20:00:00Z",
        location="History",
        created_by=manage_events_user,
    )


def _patch_status(api_client, headers, event_id, status, notify_attendees=None):
    data = {"status": status}
    if notify_attendees is not None:
        data["notify_attendees"] = notify_attendees
    return api_client.patch(
        f"/api/community/events/{event_id}/",
        data,
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestCancelEvent:
    def test_cancel_excludes_from_active_list(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled")
        response = api_client.get("/api/community/events/", **manage_events_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(upcoming_event_with_rsvp.id) not in ids

    def test_cancel_returns_cancelled_status(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_past_event_returns_400(self, api_client, manage_events_headers, past_event):
        response = _patch_status(api_client, manage_events_headers, past_event.id, "cancelled")
        assert response.status_code == 400
        assert "past" in response.json()["detail"].lower()

    def test_cancel_event_no_attendees_returns_400(
        self, api_client, manage_events_headers, upcoming_event_no_attendees
    ):
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_no_attendees.id, "cancelled"
        )
        assert response.status_code == 400
        assert "delete" in response.json()["detail"].lower()

    def test_cancel_with_notify_creates_notifications(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp, test_user
    ):
        from notifications.models import Notification, NotificationType

        response = _patch_status(
            api_client,
            manage_events_headers,
            upcoming_event_with_rsvp.id,
            "cancelled",
            notify_attendees=True,
        )
        assert response.status_code == 200
        assert Notification.objects.filter(
            recipient=test_user,
            notification_type=NotificationType.EVENT_CANCELLED,
        ).exists()

    def test_cancel_without_notify_no_notifications(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp, test_user
    ):
        from notifications.models import Notification, NotificationType

        _patch_status(
            api_client,
            manage_events_headers,
            upcoming_event_with_rsvp.id,
            "cancelled",
            notify_attendees=False,
        )
        assert not Notification.objects.filter(
            recipient=test_user,
            notification_type=NotificationType.EVENT_CANCELLED,
        ).exists()

    def test_rsvp_cancelled_event_returns_400(
        self, api_client, manage_events_headers, auth_headers, upcoming_event_with_rsvp
    ):
        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled")
        response = api_client.post(
            f"/api/community/events/{upcoming_event_with_rsvp.id}/rsvp/",
            {"status": "attending", "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_cancel_preserves_rsvps(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        from community.models import EventRSVP

        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled")
        assert EventRSVP.objects.filter(event=upcoming_event_with_rsvp).exists()

    def test_list_cancelled_events_returns_own(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled")
        response = api_client.get(
            "/api/community/events/?status=cancelled", **manage_events_headers
        )
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(upcoming_event_with_rsvp.id) in ids

    def test_list_cancelled_events_requires_auth(self, api_client, upcoming_event_with_rsvp):
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["status"])
        response = api_client.get("/api/community/events/?status=cancelled")
        assert response.status_code == 403

    def test_event_accessible_by_id_after_cancel(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "cancelled")
        response = api_client.get(
            f"/api/community/events/{upcoming_event_with_rsvp.id}/", **manage_events_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


@pytest.mark.django_db
class TestUncancel:
    def test_uncancel_by_creator(
        self, api_client, manage_events_headers, manage_events_user, upcoming_event_with_rsvp
    ):
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["status"])
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_with_rsvp.id, "active"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_uncancel_by_manager(self, api_client, manage_events_headers, upcoming_event_with_rsvp):
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["status"])
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_with_rsvp.id, "active"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_cohost_cannot_uncancel(
        self, api_client, auth_headers, test_user, manage_events_user, upcoming_event_with_rsvp
    ):
        upcoming_event_with_rsvp.created_by = manage_events_user
        upcoming_event_with_rsvp.co_hosts.add(test_user)
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["created_by", "status"])
        response = _patch_status(api_client, auth_headers, upcoming_event_with_rsvp.id, "active")
        assert response.status_code == 403

    def test_uncancel_active_event_returns_400(
        self, api_client, manage_events_headers, upcoming_event_no_attendees
    ):
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_no_attendees.id, "active"
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


@pytest.mark.django_db
class TestDeleteEvent:
    def test_delete_past_event(self, api_client, manage_events_headers, past_event):
        response = _patch_status(api_client, manage_events_headers, past_event.id, "deleted")
        assert response.status_code == 200
        past_event.refresh_from_db()
        assert past_event.status == EventStatus.DELETED
        assert past_event.deleted_at is not None

    def test_delete_active_event_no_attendees(
        self, api_client, manage_events_headers, upcoming_event_no_attendees
    ):
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_no_attendees.id, "deleted"
        )
        assert response.status_code == 200
        upcoming_event_no_attendees.refresh_from_db()
        assert upcoming_event_no_attendees.status == EventStatus.DELETED

    def test_delete_active_event_with_attendees_returns_400(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_with_rsvp.id, "deleted"
        )
        assert response.status_code == 400
        assert "cancel" in response.json()["detail"].lower()

    def test_delete_cancelled_event(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["status"])
        response = _patch_status(
            api_client, manage_events_headers, upcoming_event_with_rsvp.id, "deleted"
        )
        assert response.status_code == 200
        upcoming_event_with_rsvp.refresh_from_db()
        assert upcoming_event_with_rsvp.status == EventStatus.DELETED

    def test_deleted_event_not_in_active_list(self, api_client, manage_events_headers, past_event):
        _patch_status(api_client, manage_events_headers, past_event.id, "deleted")
        response = api_client.get("/api/community/events/", **manage_events_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(past_event.id) not in ids

    def test_deleted_event_not_in_cancelled_list(
        self, api_client, manage_events_headers, upcoming_event_with_rsvp
    ):
        upcoming_event_with_rsvp.status = EventStatus.CANCELLED
        upcoming_event_with_rsvp.save(update_fields=["status"])
        _patch_status(api_client, manage_events_headers, upcoming_event_with_rsvp.id, "deleted")
        response = api_client.get(
            "/api/community/events/?status=cancelled", **manage_events_headers
        )
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(upcoming_event_with_rsvp.id) not in ids

    def test_deleted_event_returns_404(self, api_client, manage_events_headers, past_event):
        _patch_status(api_client, manage_events_headers, past_event.id, "deleted")
        response = api_client.get(
            f"/api/community/events/{past_event.id}/", **manage_events_headers
        )
        assert response.status_code == 404

    def test_delete_requires_permission(self, api_client, auth_headers, past_event):
        response = _patch_status(api_client, auth_headers, past_event.id, "deleted")
        assert response.status_code == 403

    def test_delete_requires_auth(self, api_client, past_event):
        response = api_client.patch(
            f"/api/community/events/{past_event.id}/",
            {"status": "deleted"},
            content_type="application/json",
        )
        assert response.status_code == 401
