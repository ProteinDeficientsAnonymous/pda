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
        phone_number="+14155551234",
        password="eventmanagerpass123",
        display_name="Event Manager",
    )
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
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

    def test_created_by_name_uses_display_name(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Named Event",
                "start_datetime": "2026-05-01T18:00:00Z",
                "end_datetime": "2026-05-01T20:00:00Z",
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 201
        assert response.json()["created_by_name"] == "Event Manager"

    def test_create_event_as_regular_member(self, api_client, auth_headers, test_user):
        """Any authenticated member can create an event."""
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Member Event",
                "start_datetime": "2026-05-01T18:00:00Z",
                "end_datetime": "2026-05-01T20:00:00Z",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Member Event"
        assert data["created_by_id"] == str(test_user.pk)

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
        """A regular member cannot edit an event they did not create."""
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"title": "Blocked Update"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied."

    def test_member_can_edit_own_event(self, api_client, auth_headers, test_user):
        """A regular member can edit an event they created."""
        event = Event.objects.create(
            title="My Event",
            description="Created by member",
            start_datetime="2026-07-01T18:00:00Z",
            end_datetime="2026-07-01T20:00:00Z",
            location="Online",
            created_by=test_user,
        )
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"title": "My Updated Event"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "My Updated Event"

    def test_member_cannot_edit_others_event(self, api_client, auth_headers, manage_events_user):
        """A regular member cannot edit an event created by someone else."""
        event = Event.objects.create(
            title="Someone Else's Event",
            description="Created by manager",
            start_datetime="2026-07-01T18:00:00Z",
            end_datetime="2026-07-01T20:00:00Z",
            location="Online",
            created_by=manage_events_user,
        )
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"title": "Hijacked Title"},
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
        """A regular member cannot delete an event they did not create."""
        response = api_client.delete(
            f"/api/community/events/{sample_event.id}/",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Permission denied."

    def test_member_can_delete_own_event(self, api_client, auth_headers, test_user):
        """A regular member can delete an event they created."""
        event = Event.objects.create(
            title="My Deletable Event",
            description="Created by member",
            start_datetime="2026-08-01T18:00:00Z",
            end_datetime="2026-08-01T20:00:00Z",
            location="Online",
            created_by=test_user,
        )
        event_id = event.id
        response = api_client.delete(
            f"/api/community/events/{event_id}/",
            **auth_headers,
        )
        assert response.status_code == 204
        assert not Event.objects.filter(id=event_id).exists()

    def test_member_cannot_delete_others_event(self, api_client, auth_headers, manage_events_user):
        """A regular member cannot delete an event created by someone else."""
        event = Event.objects.create(
            title="Someone Else's Deletable Event",
            description="Created by manager",
            start_datetime="2026-08-01T18:00:00Z",
            end_datetime="2026-08-01T20:00:00Z",
            location="Online",
            created_by=manage_events_user,
        )
        response = api_client.delete(
            f"/api/community/events/{event.id}/",
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
