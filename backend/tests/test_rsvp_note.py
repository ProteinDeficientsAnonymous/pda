"""Tests for the optional message/note on an event RSVP (issue #297)."""

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="RSVP Event",
        description="An event with RSVPs enabled",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        location="Community Space",
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550302",
        password="otherpass",
        display_name="Other Member",
    )


@pytest.fixture
def other_headers(other_user):
    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestRSVPNote:
    def test_rsvp_with_note(self, api_client, auth_headers, rsvp_event, test_user):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "bringing snacks"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == "bringing snacks"
        rsvp = EventRSVP.objects.get(event=rsvp_event, user=test_user)
        assert rsvp.note == "bringing snacks"

    def test_rsvp_note_defaults_empty(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == ""

    def test_rsvp_note_updated_on_upsert(self, api_client, auth_headers, rsvp_event):
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "running 10 mins late"},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.MAYBE, "note": "actually can't make it"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == "actually can't make it"

    def test_rsvp_note_preserved_when_omitted(self, api_client, auth_headers, rsvp_event):
        # A status-only change (no note key) must not wipe an existing note.
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "bringing hummus"},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == "bringing hummus"

    def test_rsvp_note_cleared_when_empty_string(self, api_client, auth_headers, rsvp_event):
        # An explicit empty string clears the note (distinct from omitting it).
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "bringing hummus"},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == ""

    def test_rsvp_note_stripped(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "  bringing snacks  "},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == "bringing snacks"

    def test_rsvp_note_too_long_rejected(self, api_client, auth_headers, rsvp_event):
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "x" * 301},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_guest_note_visible_to_members(
        self, api_client, auth_headers, rsvp_event, other_headers
    ):
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "vegan cupcakes incoming"},
            content_type="application/json",
            **other_headers,
        )
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers)
        assert response.status_code == 200
        guests = response.json()["guests"]
        assert len(guests) == 1
        assert guests[0]["note"] == "vegan cupcakes incoming"

    def test_my_rsvp_note_empty_for_other_viewer(
        self, api_client, auth_headers, rsvp_event, other_headers
    ):
        # my_rsvp_note reflects only the requesting user's own note.
        api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "note": "my private reminder"},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **other_headers)
        assert response.status_code == 200
        assert response.json()["my_rsvp_note"] == ""
