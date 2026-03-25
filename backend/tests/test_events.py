import pytest

from community.models import Event
from users.permissions import PermissionKey
from users.roles import Role


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manage_events_user(db):
    """A non-superuser with only manage_events permission."""
    from users.models import User

    user = User.objects.create_user(
        email="eventmanager@pda.org",
        password="eventmanagerpass123",
    )
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def manage_events_headers(manage_events_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_events_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.fixture
def sample_event(db):
    return Event.objects.create(
        title="Community Meetup",
        description="Monthly gathering",
        start_datetime="2026-04-01T18:00:00Z",
        end_datetime="2026-04-01T20:00:00Z",
        location="The Vegan Cafe",
    )


# ---------------------------------------------------------------------------
# TestEventManagement
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventManagement:
    # POST /api/community/events/

    def test_create_event_success(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "New Event",
                "description": "A great event",
                "start_datetime": "2026-05-01T18:00:00Z",
                "end_datetime": "2026-05-01T20:00:00Z",
                "location": "Online",
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Event"
        assert data["description"] == "A great event"
        assert data["location"] == "Online"
        assert "id" in data

    def test_create_event_requires_permission(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Blocked Event",
                "start_datetime": "2026-05-01T18:00:00Z",
                "end_datetime": "2026-05-01T20:00:00Z",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied."

    def test_create_event_requires_auth(self, api_client):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Unauthenticated Event",
                "start_datetime": "2026-05-01T18:00:00Z",
                "end_datetime": "2026-05-01T20:00:00Z",
            },
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_create_event_defaults_optional_fields(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Minimal Event",
                "start_datetime": "2026-06-01T10:00:00Z",
                "end_datetime": "2026-06-01T11:00:00Z",
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == ""
        assert data["location"] == ""

    # PATCH /api/community/events/{id}/

    def test_update_event_success(self, api_client, manage_events_headers, sample_event):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"title": "Updated Title", "location": "New Venue"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["location"] == "New Venue"
        # Unchanged fields remain
        assert data["description"] == "Monthly gathering"

    def test_update_event_requires_permission(self, api_client, auth_headers, sample_event):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"title": "Blocked Update"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied."

    def test_update_event_requires_auth(self, api_client, sample_event):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"title": "Unauthenticated Update"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_event_not_found(self, api_client, manage_events_headers):
        response = api_client.patch(
            "/api/community/events/00000000-0000-0000-0000-000000000000/",
            {"title": "Ghost Event"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Event not found."

    def test_update_event_partial(self, api_client, manage_events_headers, sample_event):
        """PATCH with only one field should not overwrite others."""
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"description": "Updated description only"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description only"
        assert data["title"] == "Community Meetup"
        assert data["location"] == "The Vegan Cafe"

    # DELETE /api/community/events/{id}/

    def test_delete_event_success(self, api_client, manage_events_headers, sample_event):
        event_id = sample_event.id
        response = api_client.delete(
            f"/api/community/events/{event_id}/",
            **manage_events_headers,
        )
        assert response.status_code == 204
        assert not Event.objects.filter(id=event_id).exists()

    def test_delete_event_requires_permission(self, api_client, auth_headers, sample_event):
        response = api_client.delete(
            f"/api/community/events/{sample_event.id}/",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied."

    def test_delete_event_requires_auth(self, api_client, sample_event):
        response = api_client.delete(
            f"/api/community/events/{sample_event.id}/",
        )
        assert response.status_code == 401

    def test_delete_event_not_found(self, api_client, manage_events_headers):
        response = api_client.delete(
            "/api/community/events/00000000-0000-0000-0000-000000000000/",
            **manage_events_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Event not found."
