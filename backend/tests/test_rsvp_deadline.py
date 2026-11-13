from datetime import timedelta

import pytest
from community.models import Event
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._time import future_iso

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def host_headers(test_user):
    return auth_headers_for(test_user)


def _event(host, deadline_in: timedelta | None) -> Event:
    return Event.objects.create(
        title="Deadline Event",
        start_datetime=future_iso(days=7),
        rsvp_enabled=True,
        rsvp_deadline=None if deadline_in is None else timezone.now() + deadline_in,
        created_by=host,
    )


def _patch(api_client, event, headers, body):
    return api_client.patch(
        f"{EVENTS_URL}{event.id}/", body, content_type="application/json", **headers
    )


@pytest.mark.django_db
class TestSetDeadline:
    def test_create_with_deadline(self, api_client, host_headers):
        response = api_client.post(
            EVENTS_URL,
            {"title": "New", "start_datetime": future_iso(7), "rsvp_deadline": future_iso(5)},
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 201
        assert response.json()["rsvp_deadline"] is not None
        assert Event.objects.get(id=response.json()["id"]).rsvp_deadline is not None

    def test_create_without_deadline(self, api_client, host_headers):
        response = api_client.post(
            EVENTS_URL,
            {"title": "New", "start_datetime": future_iso(7)},
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 201
        assert response.json()["rsvp_deadline"] is None

    def test_create_rejects_deadline_after_start(self, api_client, host_headers):
        response = api_client.post(
            EVENTS_URL,
            {"title": "New", "start_datetime": future_iso(7), "rsvp_deadline": future_iso(8)},
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_DEADLINE_AFTER_START, "rsvp_deadline")

    def test_patch_sets_and_clears_deadline(self, api_client, test_user, host_headers):
        event = _event(test_user, None)

        set_resp = _patch(api_client, event, host_headers, {"rsvp_deadline": future_iso(5)})
        assert set_resp.status_code == 200
        event.refresh_from_db()
        assert event.rsvp_deadline is not None

        clear_resp = _patch(api_client, event, host_headers, {"rsvp_deadline": None})
        assert clear_resp.status_code == 200
        assert clear_resp.json()["rsvp_deadline"] is None
        event.refresh_from_db()
        assert event.rsvp_deadline is None

    def test_patch_rejects_start_moved_before_deadline(self, api_client, test_user, host_headers):
        event = _event(test_user, timedelta(days=5))
        response = _patch(api_client, event, host_headers, {"start_datetime": future_iso(3)})
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_DEADLINE_AFTER_START)

    def test_patch_allows_deadline_on_tbd_event(self, api_client, test_user, host_headers):
        event = _event(test_user, None)
        response = _patch(
            api_client,
            event,
            host_headers,
            {"datetime_tbd": True, "start_datetime": None, "rsvp_deadline": future_iso(30)},
        )
        assert response.status_code == 200
