"""Tests for event create/update datetime validation."""

from datetime import datetime, timedelta

import pytest
from community._validation import Code
from community.models import Event
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso, past_iso


def _naive_future_iso(days: int, hours: int = 0) -> str:
    return (datetime.now() + timedelta(days=days, hours=hours)).replace(microsecond=0).isoformat()


@pytest.fixture
def manage_events_headers(db):
    user = User.objects.create_user(
        phone_number="+14155551236",
        password="eventmanagerpass123",
        first_name="Event",
        last_name="Manager",
    )
    role = Role.objects.create(
        name="event_manager_datetime", permissions=[PermissionKey.MANAGE_EVENTS]
    )
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def sample_event(db):
    return Event.objects.create(
        title="Community Meetup",
        start_datetime=future_iso(days=7),
        end_datetime=future_iso(days=7, hours=2),
    )


@pytest.mark.django_db
class TestEventDatetimeValidation:
    def test_create_event_without_end_datetime(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Open-ended Event",
                "start_datetime": future_iso(days=14),
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 201
        assert response.json()["end_datetime"] is None

    def test_create_event_end_before_start_returns_400(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Bad Event",
                "start_datetime": future_iso(days=14, hours=2),
                "end_datetime": future_iso(days=14),
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.END_BEFORE_START, "end_datetime")

    @pytest.mark.parametrize("field", ["start_datetime", "end_datetime"])
    def test_create_event_naive_datetime_returns_422(
        self, api_client, manage_events_headers, field
    ):
        payload = {
            "title": "Naive Event",
            "start_datetime": future_iso(days=14),
            "end_datetime": future_iso(days=14, hours=2),
        }
        payload[field] = _naive_future_iso(days=14, hours=1)
        response = api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.DATETIME_OFFSET_REQUIRED, field)

    def test_create_event_in_past_returns_400(self, api_client, manage_events_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Past Event",
                "start_datetime": past_iso(days=90),
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_create_event_in_past_allowed_when_datetime_tbd(
        self, api_client, manage_events_headers
    ):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "TBD Event",
                "start_datetime": past_iso(days=90),
                "datetime_tbd": True,
            },
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 201

    def test_update_event_start_to_past_returns_400(
        self, api_client, manage_events_headers, sample_event
    ):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"start_datetime": past_iso(days=90)},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_update_event_non_date_fields_on_past_event(
        self, api_client, manage_events_headers, db
    ):
        """Updating non-date fields on a past event should succeed."""
        past_event = Event.objects.create(
            title="Old Meetup",
            start_datetime=past_iso(days=90),
        )
        response = api_client.patch(
            f"/api/community/events/{past_event.id}/",
            {"title": "Updated Old Meetup"},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Old Meetup"

    def test_update_event_clear_end_datetime(self, api_client, manage_events_headers, sample_event):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"end_datetime": None},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 200
        assert response.json()["end_datetime"] is None

    def test_update_event_end_before_start_returns_400(
        self, api_client, manage_events_headers, sample_event
    ):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {"end_datetime": future_iso(days=6)},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.END_BEFORE_START, "end_datetime")

    @pytest.mark.parametrize("field", ["start_datetime", "end_datetime"])
    def test_update_event_naive_datetime_returns_422(
        self, api_client, manage_events_headers, sample_event, field
    ):
        response = api_client.patch(
            f"/api/community/events/{sample_event.id}/",
            {field: _naive_future_iso(days=60)},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.DATETIME_OFFSET_REQUIRED, field)
