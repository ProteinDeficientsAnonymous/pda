"""Tests for the past-event guard on cohost invites (issue #385).

A separate file from test_event_cohost_invites.py to honor the 500-line cap.
"""

import json
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import (
    Event,
    EventCoHostInvite,
    EventStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code
from tests.conftest import future_iso, past_iso

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "Member") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        display_name=name,
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _create_active_event(api_client, creator: User, co_host_ids: list[str]) -> str:
    response = api_client.post(
        "/api/community/events/",
        data=json.dumps(
            {
                "title": "Community Potluck",
                "start_datetime": future_iso(days=30),
                "end_datetime": future_iso(days=30, hours=2),
                "status": EventStatus.ACTIVE,
                "co_host_ids": co_host_ids,
            }
        ),
        content_type="application/json",
        **_auth_headers(creator),
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _make_event_past(event_id: str) -> None:
    past = timezone.now() - timedelta(days=1)
    Event.objects.filter(pk=event_id).update(
        start_datetime=past - timedelta(hours=1),
        end_datetime=past,
    )


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550311", "Creator")


@pytest.fixture
def invitee(db) -> User:
    return _make_user("+12025550312", "Invitee")


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPastEventGuard:
    def test_create_with_cohost_on_past_start_already_blocked_by_event_validator(
        self, api_client, creator, invitee
    ):
        # Sanity check: creating an event with a past start_datetime is blocked
        # at the EventIn validator (422). So this guard only matters via patch
        # onto an event that *became* past after creation, and via direct
        # callers of diff_cohost_invites that bypass EventIn.
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Past Potluck",
                    "start_datetime": past_iso(days=1),
                    "end_datetime": past_iso(days=1),
                    "status": EventStatus.ACTIVE,
                    "co_host_ids": [str(invitee.pk)],
                }
            ),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE)

    def test_patch_add_cohost_on_past_event_rejected(self, api_client, creator, invitee):
        event_id = _create_active_event(api_client, creator, co_host_ids=[])
        _make_event_past(event_id)
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": [str(invitee.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        assert_error_code(response, Code.CoHostInvite.EVENT_IS_PAST)
        assert EventCoHostInvite.objects.filter(event_id=event_id).count() == 0

    def test_patch_remove_cohost_on_past_event_still_works(self, api_client, creator, invitee):
        # Removal is housekeeping — should keep working after the event ends.
        event_id = _create_active_event(api_client, creator, co_host_ids=[str(invitee.pk)])
        _make_event_past(event_id)
        # Invite would have been lazily expired on read; patch with empty list
        # is a noop for the now-EXPIRED row (rescind branch only acts on
        # PENDING/ACCEPTED).
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": []}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200

    def test_patch_with_no_diff_on_past_event_is_noop(self, api_client, creator, invitee):
        # If the input matches the existing accepted set, no upsert happens —
        # the guard should NOT fire just because the event is past.
        event_id = _create_active_event(api_client, creator, co_host_ids=[str(invitee.pk)])
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        # Accept first so the user is an accepted co-host.
        api_client.post(
            f"/api/community/events/{event_id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        _make_event_past(event_id)
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": [str(invitee.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
