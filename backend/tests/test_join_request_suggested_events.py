"""Tests for the events suggested in a tentative applicant's welcome message."""

import logging
import uuid
from datetime import timedelta

import pytest
from community.models import (
    Club,
    Event,
    EventStatus,
    EventType,
    JoinRequest,
    PageVisibility,
)
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code


def _url(join_request_id) -> str:
    return f"/api/community/join-requests/{join_request_id}/suggested-events/"


def _join_request(*clubs: Club) -> JoinRequest:
    join_request = JoinRequest.objects.create(first_name="Sprout", phone_number="+16505551234")
    join_request.interested_clubs.set(clubs)
    return join_request


def _event(title, event_type, days, **fields) -> Event:
    return Event.objects.create(
        title=title,
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=days),
        **fields,
    )


def _official(title, days, **fields) -> Event:
    return _event(title, EventType.OFFICIAL, days, rsvp_enabled=True, **fields)


@pytest.fixture
def book(db):
    return Club.objects.create(name="book club")


def _get(api_client, headers, join_request):
    response = api_client.get(_url(join_request.id), **headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
class TestNextOfficialEvent:
    def test_is_the_soonest_upcoming(self, api_client, vettor_headers):
        _official("past walk", -3)
        _official("later walk", 20)
        soon = _official("soon walk", 2)
        _event("community thing", EventType.COMMUNITY, 1, rsvp_enabled=True)

        body = _get(api_client, vettor_headers, _join_request())

        assert body["next_official_event"]["id"] == str(soon.id)
        assert body["next_official_event"]["title"] == "soon walk"

    def test_skips_cancelled_draft_invite_only_tbd_and_rsvp_disabled(
        self, api_client, vettor_headers
    ):
        _official("cancelled", 1, status=EventStatus.CANCELLED)
        _official("draft", 1, status=EventStatus.DRAFT)
        _official("secret", 1, visibility=PageVisibility.INVITE_ONLY)
        _official("tbd", 1, datetime_tbd=True)
        _event("no rsvp", EventType.OFFICIAL, 1)
        members = _official("members", 2, visibility=PageVisibility.MEMBERS_ONLY)

        body = _get(api_client, vettor_headers, _join_request())

        assert body["next_official_event"]["id"] == str(members.id)

    def test_nothing_upcoming(self, api_client, vettor_headers, book):
        body = _get(api_client, vettor_headers, _join_request(book))

        assert body == {"next_official_event": None}


@pytest.mark.django_db
class TestAccess:
    def test_requires_approve_join_requests(self, api_client, auth_headers, caplog):
        join_request = _join_request()
        audit_logger = logging.getLogger("pda.audit")
        audit_logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.WARNING, logger="pda.audit"):
                response = api_client.get(_url(join_request.id), **auth_headers)
        finally:
            audit_logger.removeHandler(caplog.handler)

        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)
        record = next(
            r for r in caplog.records if getattr(r, "action", None) == "permission_denied"
        )
        assert record.target_type == "join_request"
        assert record.target_id == str(join_request.id)

    def test_unknown_join_request(self, api_client, vettor_headers):
        response = api_client.get(_url(uuid.uuid4()), **vettor_headers)

        assert response.status_code == 404
        assert_error_code(response, Code.JoinRequest.NOT_FOUND)
