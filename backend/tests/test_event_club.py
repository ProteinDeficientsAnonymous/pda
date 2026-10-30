import pytest
from community.models import Event, EventType
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._auth import auth_headers_for


@pytest.fixture
def club_event_user(db):
    """A user with tag_club_event permission."""
    user = User.objects.create_user(
        phone_number="+14155558888",
        password="clubpass123",
        first_name="Club",
        last_name="Tagger",
    )
    role = Role.objects.create(name="club_tagger", permissions=[PermissionKey.TAG_CLUB_EVENT])
    user.roles.add(role)
    return user


@pytest.fixture
def club_event_headers(club_event_user):
    return auth_headers_for(club_event_user)


class TestClubEventVisibility:
    """Club events, like official, are public and require a tag permission."""

    def _club_payload(self, **overrides):
        payload = {
            "title": "Club Event",
            "description": "",
            "datetime_tbd": True,
            "event_type": "club",
            "visibility": "public",
        }
        payload.update(overrides)
        return payload

    def test_list_shows_club_event_to_anonymous(self, api_client, club_event_user):
        event = Event.objects.create(
            title="Club Meetup",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            event_type=EventType.CLUB,
            created_by=club_event_user,
        )
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        assert str(event.id) in [e["id"] for e in response.json()]

    def test_create_club_event_requires_permission(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/",
            self._club_payload(),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_create_club_event_allowed_with_permission(self, api_client, club_event_headers):
        response = api_client.post(
            "/api/community/events/",
            self._club_payload(),
            content_type="application/json",
            **club_event_headers,
        )
        assert response.status_code == 201
        assert response.json()["event_type"] == "club"

    def test_create_club_event_rejects_non_public_visibility(self, api_client, club_event_headers):
        response = api_client.post(
            "/api/community/events/",
            self._club_payload(visibility="members_only"),
            content_type="application/json",
            **club_event_headers,
        )
        assert response.status_code == 400
