"""End-to-end tests for the event comments API."""

import json

import pytest
from community.models import Event, EventRSVP, RSVPStatus

from tests.conftest import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        created_by=test_user,
    )


@pytest.mark.django_db
class TestGetComments:
    def test_get_empty_unauthed(self, api_client, event):
        response = api_client.get(f"/api/community/events/{event.id}/comments/")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["items"] == []
        assert body["can_post"] is False
        assert body["cannot_post_reason"] == "login_required"


@pytest.fixture
def rsvp_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550303",
        password="rsvppass123",
        display_name="RSVP Member",
    )


@pytest.fixture
def rsvp_headers(rsvp_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(rsvp_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.fixture
def event_with_rsvp(db, event, rsvp_user):
    EventRSVP.objects.create(event=event, user=rsvp_user, status=RSVPStatus.ATTENDING)
    return event


@pytest.mark.django_db
class TestPostComment:
    def test_post_requires_auth(self, api_client, event):
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "hi"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_post_requires_rsvp(self, api_client, auth_headers, event):
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "hi"}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "comment.rsvp_required"

    def test_post_creates_comment(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": "first comment"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["body"] == "first comment"
        assert body["is_deleted"] is False
        assert body["replies"] == []
        assert body["reactions"] == []
        assert body["can_delete"] is True  # author can delete

    def test_post_rejects_empty_body(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": ""}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422

    def test_post_rejects_oversize_body(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": "x" * 501}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422
