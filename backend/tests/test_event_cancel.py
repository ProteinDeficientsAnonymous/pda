"""Tests for event cancel/uncancel endpoints."""

import pytest
from community.models import Event
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
def sample_event(db):
    return Event.objects.create(
        title="Cancel Test Event",
        description="For cancel tests",
        start_datetime="2026-04-01T18:00:00Z",
        end_datetime="2026-04-01T20:00:00Z",
        location="The Vegan Cafe",
    )


@pytest.mark.django_db
class TestCancelledEvents:
    """Tests for cancel/uncancel event behaviour."""

    def test_cancel_event_excludes_from_list(self, api_client, manage_events_headers, sample_event):
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        response = api_client.get("/api/community/events/", **manage_events_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_event.id) not in ids

    def test_cancel_event_accessible_by_id(self, api_client, manage_events_headers, sample_event):
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        response = api_client.get(
            f"/api/community/events/{sample_event.id}/", **manage_events_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_update_cancelled_event_returns_400(
        self, api_client, manage_events_headers, sample_event
    ):
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"title": "New Title"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    def test_rsvp_cancelled_event_returns_400(
        self, api_client, manage_events_headers, auth_headers, sample_event
    ):
        sample_event.rsvp_enabled = True
        sample_event.save(update_fields=["rsvp_enabled"])
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/rsvp/",
            {"status": "attending", "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    def test_uncancel_by_creator(self, api_client, auth_headers, test_user, sample_event):
        sample_event.created_by = test_user
        sample_event.save(update_fields=["created_by"])
        api_client.delete(f"/api/community/events/{sample_event.id}/", **auth_headers)
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/uncancel/", **auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_uncancel_by_manager(self, api_client, manage_events_headers, sample_event):
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/uncancel/", **manage_events_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_cohost_cannot_uncancel(
        self, api_client, auth_headers, test_user, manage_events_user, sample_event
    ):
        from community.models import EventStatus

        sample_event.created_by = manage_events_user
        sample_event.co_hosts.add(test_user)
        sample_event.save(update_fields=["created_by"])
        sample_event.status = EventStatus.CANCELLED
        sample_event.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/uncancel/", **auth_headers
        )
        assert response.status_code == 403

    def test_uncancel_active_event_returns_400(
        self, api_client, manage_events_headers, sample_event
    ):
        response = api_client.post(
            f"/api/community/events/{sample_event.id}/uncancel/", **manage_events_headers
        )
        assert response.status_code == 400
        assert "not cancelled" in response.json()["detail"].lower()

    def test_list_cancelled_events_returns_own(
        self, api_client, auth_headers, test_user, sample_event
    ):
        sample_event.created_by = test_user
        sample_event.save(update_fields=["created_by"])
        api_client.delete(f"/api/community/events/{sample_event.id}/", **auth_headers)
        response = api_client.get("/api/community/events/?status=cancelled", **auth_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_event.id) in ids

    def test_list_cancelled_events_requires_auth(self, api_client, sample_event):
        from community.models import EventStatus

        sample_event.status = EventStatus.CANCELLED
        sample_event.save(update_fields=["status"])
        response = api_client.get("/api/community/events/?status=cancelled")
        assert response.status_code == 403

    def test_cancel_preserves_rsvps(
        self, api_client, manage_events_headers, test_user, sample_event
    ):
        from community.models import EventRSVP

        sample_event.rsvp_enabled = True
        sample_event.save(update_fields=["rsvp_enabled"])
        EventRSVP.objects.create(event=sample_event, user=test_user, status="attending")
        api_client.delete(f"/api/community/events/{sample_event.id}/", **manage_events_headers)
        assert EventRSVP.objects.filter(event=sample_event).exists()
