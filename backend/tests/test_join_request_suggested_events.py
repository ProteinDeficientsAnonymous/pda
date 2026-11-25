"""Tests for the events suggested in a tentative applicant's welcome message."""

import uuid
from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventStatus,
    EventTag,
    EventType,
    JoinRequest,
    PageVisibility,
)
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code

CLUBS_QUESTION_ID = "266d97e3-56c9-4edc-805e-85a234cc58f9"


def _url(join_request_id) -> str:
    return f"/api/community/join-requests/{join_request_id}/suggested-events/"


def _join_request(*clubs: str) -> JoinRequest:
    return JoinRequest.objects.create(
        first_name="Sprout",
        phone_number="+16505551234",
        custom_answers={
            "q-vegan": {"label": "are you vegan?", "answer": "yes"},
            CLUBS_QUESTION_ID: {
                "label": "which of the clubs are you interested in?",
                "answer": list(clubs),
            },
        },
    )


def _event(title, event_type, days, *tags, **fields) -> Event:
    event = Event.objects.create(
        title=title,
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=days),
        **fields,
    )
    event.tags.set(tags)
    return event


@pytest.fixture
def book_tag(db):
    return EventTag.objects.create(name="book club")


@pytest.fixture
def movie_tag(db):
    return EventTag.objects.create(name="movie club")


def _get(api_client, headers, join_request):
    response = api_client.get(_url(join_request.id), **headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
class TestSuggestedEvents:
    def test_next_official_event_is_the_soonest_upcoming(self, api_client, vettor_headers):
        _event("past walk", EventType.OFFICIAL, -3)
        _event("later walk", EventType.OFFICIAL, 20)
        soon = _event("soon walk", EventType.OFFICIAL, 2)
        _event("community thing", EventType.COMMUNITY, 1)

        body = _get(api_client, vettor_headers, _join_request())

        assert body["next_official_event"]["id"] == str(soon.id)
        assert body["next_official_event"]["title"] == "soon walk"

    def test_skips_cancelled_draft_invite_only_and_tbd_events(self, api_client, vettor_headers):
        _event("cancelled", EventType.OFFICIAL, 1, status=EventStatus.CANCELLED)
        _event("draft", EventType.OFFICIAL, 1, status=EventStatus.DRAFT)
        _event("secret", EventType.OFFICIAL, 1, visibility=PageVisibility.INVITE_ONLY)
        _event("tbd", EventType.OFFICIAL, 1, datetime_tbd=True)
        members = _event("members", EventType.OFFICIAL, 2, visibility=PageVisibility.MEMBERS_ONLY)

        body = _get(api_client, vettor_headers, _join_request())

        assert body["next_official_event"]["id"] == str(members.id)

    def test_club_event_matches_a_chosen_club_by_tag(
        self, api_client, vettor_headers, book_tag, movie_tag
    ):
        _event("movie night", EventType.CLUB, 8, movie_tag)
        book = _event("book club", EventType.CLUB, 10, book_tag)

        body = _get(api_client, vettor_headers, _join_request("book club", "board game club"))

        assert body["club_event"]["id"] == str(book.id)

    def test_club_event_is_at_least_a_week_out(self, api_client, vettor_headers, book_tag):
        _event("too soon", EventType.CLUB, 6, book_tag)
        later = _event("next month", EventType.CLUB, 30, book_tag)

        body = _get(api_client, vettor_headers, _join_request("book club"))

        assert body["club_event"]["id"] == str(later.id)

    def test_tag_name_inside_a_longer_option_matches(self, api_client, vettor_headers):
        dogs = EventTag.objects.create(name="Doggie Meetup")
        event = _event("pup picnic", EventType.CLUB, 9, dogs)

        body = _get(
            api_client,
            vettor_headers,
            _join_request("doggie meetup club (must be dog parent // guardian)"),
        )

        assert body["club_event"]["id"] == str(event.id)

    def test_only_club_events_are_suggested_as_the_club_event(
        self, api_client, vettor_headers, book_tag
    ):
        _event("official with tag", EventType.OFFICIAL, 9, book_tag)

        body = _get(api_client, vettor_headers, _join_request("book club"))

        assert body["club_event"] is None

    def test_no_club_event_without_a_matching_answer(self, api_client, vettor_headers, book_tag):
        _event("book club", EventType.CLUB, 10, book_tag)

        assert _get(api_client, vettor_headers, _join_request("movie club"))["club_event"] is None

    def test_no_club_event_when_no_clubs_chosen(self, api_client, vettor_headers, book_tag):
        _event("book club", EventType.CLUB, 10, book_tag)

        assert _get(api_client, vettor_headers, _join_request())["club_event"] is None

    def test_event_with_two_matching_tags_is_returned_once(
        self, api_client, vettor_headers, book_tag, movie_tag
    ):
        both = _event("book-to-movie night", EventType.CLUB, 10, book_tag, movie_tag)

        body = _get(api_client, vettor_headers, _join_request("book club", "movie club"))

        assert body["club_event"]["id"] == str(both.id)

    def test_nothing_upcoming(self, api_client, vettor_headers):
        body = _get(api_client, vettor_headers, _join_request("book club"))

        assert body == {"next_official_event": None, "club_event": None}

    def test_requires_approve_join_requests(self, api_client, auth_headers):
        response = api_client.get(_url(_join_request().id), **auth_headers)

        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_unknown_join_request(self, api_client, vettor_headers):
        response = api_client.get(_url(uuid.uuid4()), **vettor_headers)

        assert response.status_code == 404
        assert_error_code(response, Code.JoinRequest.NOT_FOUND)
