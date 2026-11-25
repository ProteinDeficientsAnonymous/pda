"""Tests for which club a club event belongs to."""

import uuid
from datetime import timedelta

import pytest
from community.models import Club, Event, EventType, PageVisibility
from community.validation import Code
from django.utils import timezone
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._time import future_iso
from tests._users import make_user

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def host(db):
    return make_user(PermissionKey.TAG_CLUB_EVENT)


@pytest.fixture
def host_headers(host):
    return auth_headers_for(host)


@pytest.fixture
def book_club(db):
    return Club.objects.create(name="book club", requirements="")


def _create(api_client, headers, event_type=EventType.CLUB, **fields):
    payload = {
        "title": "Meetup",
        "start_datetime": future_iso(days=10),
        "event_type": event_type,
        "visibility": PageVisibility.PUBLIC,
        **fields,
    }
    return api_client.post(EVENTS_URL, payload, content_type="application/json", **headers)


def _patch(api_client, headers, event, **fields):
    return api_client.patch(
        f"{EVENTS_URL}{event.id}/", fields, content_type="application/json", **headers
    )


@pytest.mark.django_db
class TestCreate:
    def test_club_event_saves_its_club(self, api_client, host_headers, book_club):
        response = _create(api_client, host_headers, club_id=str(book_club.id))

        assert response.status_code == 201
        assert response.json()["club"] == {
            "id": str(book_club.id),
            "name": "book club",
            "requirements": "",
        }
        assert Event.objects.get().club == book_club

    def test_club_event_needs_a_club(self, api_client, host_headers):
        response = _create(api_client, host_headers)

        assert response.status_code == 422
        assert_error_code(response, Code.Event.CLUB_REQUIRED)
        assert not Event.objects.exists()

    def test_unknown_club(self, api_client, host_headers):
        response = _create(api_client, host_headers, club_id=str(uuid.uuid4()))

        assert response.status_code == 422
        assert_error_code(response, Code.Club.NOT_FOUND)

    def test_other_types_ignore_a_club(self, api_client, host_headers, book_club):
        response = _create(api_client, host_headers, EventType.COMMUNITY, club_id=str(book_club.id))

        assert response.status_code == 201
        assert response.json()["club"] is None
        assert Event.objects.get().club is None


@pytest.mark.django_db
class TestUpdate:
    def _club_event(self, api_client, headers, club):
        response = _create(api_client, headers, club_id=str(club.id))
        assert response.status_code == 201
        return Event.objects.get(id=response.json()["id"])

    def test_change_club(self, api_client, host_headers, book_club):
        event = self._club_event(api_client, host_headers, book_club)
        movie_club = Club.objects.create(name="movie club")

        response = _patch(api_client, host_headers, event, club_id=str(movie_club.id))

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.club == movie_club

    def test_cannot_clear_a_club_events_club(self, api_client, host_headers, book_club):
        event = self._club_event(api_client, host_headers, book_club)

        response = _patch(api_client, host_headers, event, club_id=None)

        assert_error_code(response, Code.Event.CLUB_REQUIRED)
        event.refresh_from_db()
        assert event.club == book_club

    def test_becoming_a_club_event_needs_a_club(self, api_client, host, host_headers, book_club):
        event = Event.objects.create(
            title="hang",
            event_type=EventType.COMMUNITY,
            start_datetime=timezone.now() + timedelta(days=10),
            created_by=host,
        )

        missing = _patch(api_client, host_headers, event, event_type=EventType.CLUB)
        given = _patch(
            api_client,
            host_headers,
            event,
            event_type=EventType.CLUB,
            club_id=str(book_club.id),
        )

        assert_error_code(missing, Code.Event.CLUB_REQUIRED)
        assert given.status_code == 200
        event.refresh_from_db()
        assert event.club == book_club

    def test_leaving_club_type_drops_the_club(self, api_client, host_headers, book_club):
        event = self._club_event(api_client, host_headers, book_club)

        response = _patch(api_client, host_headers, event, event_type=EventType.COMMUNITY)

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.club is None

    def test_older_club_event_without_a_club_can_still_be_edited(
        self, api_client, host, host_headers
    ):
        event = Event.objects.create(
            title="old", event_type=EventType.CLUB, datetime_tbd=True, created_by=host
        )

        response = _patch(api_client, host_headers, event, title="renamed")

        assert response.status_code == 200

    def test_deleting_a_club_keeps_its_events(self, api_client, host_headers, book_club):
        event = self._club_event(api_client, host_headers, book_club)

        book_club.delete()

        event.refresh_from_db()
        assert event.club is None
