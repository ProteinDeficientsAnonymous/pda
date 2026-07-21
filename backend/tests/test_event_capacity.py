"""Tests for RSVP capacity limits and waitlist behaviour."""

import json
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(phone, name):
    return User.objects.create_user(
        phone_number=phone,
        password="Testpass123!",
        first_name=name,
        last_name="",
    )


def _jwt_headers(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def user1(db):
    return _make_user("+14155559001", "User One")


@pytest.fixture
def user2(db):
    return _make_user("+14155559002", "User Two")


@pytest.fixture
def user3(db):
    return _make_user("+14155559003", "User Three")


@pytest.fixture
def user4(db):
    return _make_user("+14155559004", "User Four")


@pytest.fixture
def headers1(user1):
    return _jwt_headers(user1)


@pytest.fixture
def headers2(user2):
    return _jwt_headers(user2)


@pytest.fixture
def headers3(user3):
    return _jwt_headers(user3)


@pytest.fixture
def headers4(user4):
    return _jwt_headers(user4)


@pytest.fixture
def capped_event(db, test_user):
    return Event.objects.create(
        title="Capped Event",
        start_datetime=future_iso(days=30),
        rsvp_enabled=True,
        max_attendees=2,
        allow_plus_ones=True,
        created_by=test_user,
    )


@pytest.fixture
def unlimited_event(db):
    return Event.objects.create(
        title="Unlimited Event",
        start_datetime=future_iso(days=30),
        rsvp_enabled=True,
    )


def _rsvp(api_client, event, headers, status="attending", has_plus_one=False):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status, "has_plus_one": has_plus_one},
        content_type="application/json",
        **headers,
    )


# ---------------------------------------------------------------------------
# TestEventCapacity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventCapacity:
    def test_rsvp_within_capacity(self, api_client, capped_event, headers1):
        resp = _rsvp(api_client, capped_event, headers1)
        assert resp.status_code == 200
        assert resp.json()["my_rsvp"] == RSVPStatus.ATTENDING

    def test_auto_waitlist_at_capacity(
        self, api_client, capped_event, headers1, headers2, headers3
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        resp = _rsvp(api_client, capped_event, headers3)
        assert resp.status_code == 200
        assert resp.json()["my_rsvp"] == RSVPStatus.WAITLISTED

    def test_plus_one_counts_toward_capacity(self, api_client, capped_event, headers1, headers2):
        # user1 with +1 fills both spots (max=2)
        _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        resp = _rsvp(api_client, capped_event, headers2)
        assert resp.status_code == 200
        assert resp.json()["my_rsvp"] == RSVPStatus.WAITLISTED

    def test_plus_one_ignored_when_event_disallows(
        self, api_client, test_user, headers1, headers2, user1
    ):
        event = Event.objects.create(
            title="No Plus Ones",
            start_datetime=future_iso(days=30),
            rsvp_enabled=True,
            max_attendees=2,
            allow_plus_ones=False,
            created_by=test_user,
        )
        resp = _rsvp(api_client, event, headers1, has_plus_one=True)
        assert resp.status_code == 200
        assert resp.json()["my_rsvp"] == RSVPStatus.ATTENDING
        assert EventRSVP.objects.get(event=event, user=user1).has_plus_one is False
        # +1 was dropped, so the second spot is still open (not consumed).
        resp2 = _rsvp(api_client, event, headers2)
        assert resp2.json()["my_rsvp"] == RSVPStatus.ATTENDING

    def test_plus_one_denied_at_capacity(self, api_client, capped_event, headers1, headers2):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        # user1 already attending; tries to add +1 (would exceed capacity)
        resp = _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        assert resp.status_code == 400
        assert resp.json()["detail"][0]["code"] == "event.no_plus_one_spots"

    def test_waitlisted_keeps_plus_one(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers2, headers3
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3, has_plus_one=True)
        rsvp = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp.status == RSVPStatus.WAITLISTED
        assert rsvp.has_plus_one is True

    def test_cannot_set_waitlisted_directly(self, api_client, capped_event, headers1):
        resp = _rsvp(api_client, capped_event, headers1, status="waitlisted")
        assert resp.status_code == 400

    def test_no_limit_allows_unlimited(
        self, api_client, unlimited_event, headers1, headers2, headers3
    ):
        for h in (headers1, headers2, headers3):
            resp = _rsvp(api_client, unlimited_event, h)
            assert resp.status_code == 200
            assert resp.json()["my_rsvp"] == RSVPStatus.ATTENDING


# ---------------------------------------------------------------------------
# TestCapacityCounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCapacityCounts:
    def test_attending_count_includes_plus_ones(
        self, api_client, capped_event, headers1, auth_headers
    ):
        _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        resp = api_client.get(f"/api/community/events/{capped_event.id}/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["attending_count"] == 2  # 1 person + 1 guest

    def test_waitlisted_count_in_detail(  # noqa: PLR0913
        self, api_client, capped_event, headers1, headers2, headers3, auth_headers
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3)  # waitlisted
        resp = api_client.get(f"/api/community/events/{capped_event.id}/", **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["waitlisted_count"] == 1

    def test_counts_in_list_endpoint(self, api_client, capped_event, headers1, auth_headers):
        _rsvp(api_client, capped_event, headers1)
        resp = api_client.get("/api/community/events/", **auth_headers)
        assert resp.status_code == 200
        event_data = next(e for e in resp.json() if e["id"] == str(capped_event.id))
        assert event_data["attending_count"] == 1
        assert event_data["max_attendees"] == 2


# ---------------------------------------------------------------------------
# TestMaxAttendeesValidation (#362)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMaxAttendeesValidation:
    @staticmethod
    def _future_iso(days: int = 30) -> str:
        return (timezone.now() + timedelta(days=days)).isoformat()

    def test_create_rejects_zero_max_attendees(self, api_client, auth_headers):
        resp = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "No Seats",
                    "start_datetime": self._future_iso(),
                    "rsvp_enabled": True,
                    "max_attendees": 0,
                }
            ),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        assert any(
            e["code"] == Code.Event.MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE
            for e in resp.json()["detail"]
        )

    def test_create_accepts_null_max_attendees(self, api_client, auth_headers):
        resp = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Unlimited",
                    "start_datetime": self._future_iso(),
                    "rsvp_enabled": True,
                    "max_attendees": None,
                }
            ),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 201

    def test_patch_rejects_zero_max_attendees(self, api_client, capped_event, auth_headers):
        resp = api_client.patch(
            f"/api/community/events/{capped_event.id}/",
            data=json.dumps({"max_attendees": 0}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        assert any(
            e["code"] == Code.Event.MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE
            for e in resp.json()["detail"]
        )

    def test_patch_accepts_null_max_attendees(self, api_client, capped_event, auth_headers):
        resp = api_client.patch(
            f"/api/community/events/{capped_event.id}/",
            data=json.dumps({"max_attendees": None}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestListMyRsvp:
    """The list endpoint surfaces the viewer's own RSVP so calendar / my-events
    cards can show RSVP state without a per-card detail fetch (issue #566)."""

    def _list(self, api_client, headers=None):
        return api_client.get("/api/community/events/", **(headers or {}))

    def _find(self, resp, event):
        return next(e for e in resp.json() if e["id"] == str(event.id))

    def test_list_includes_viewer_rsvp(self, api_client, unlimited_event, headers1):
        _rsvp(api_client, unlimited_event, headers1, status=RSVPStatus.MAYBE)
        resp = self._list(api_client, headers1)
        assert resp.status_code == 200
        assert self._find(resp, unlimited_event)["my_rsvp"] == RSVPStatus.MAYBE

    def test_list_my_rsvp_null_without_response(self, api_client, unlimited_event, headers1):
        resp = self._list(api_client, headers1)
        assert resp.status_code == 200
        assert self._find(resp, unlimited_event)["my_rsvp"] is None

    def test_list_my_rsvp_is_per_viewer(self, api_client, unlimited_event, headers1, headers2):
        _rsvp(api_client, unlimited_event, headers1, status=RSVPStatus.ATTENDING)
        # user2 hasn't responded — their list view must not see user1's status.
        resp = self._list(api_client, headers2)
        assert self._find(resp, unlimited_event)["my_rsvp"] is None

    def test_list_my_rsvp_null_for_unauthed(self, api_client, unlimited_event, headers1):
        _rsvp(api_client, unlimited_event, headers1, status=RSVPStatus.ATTENDING)
        resp = self._list(api_client)
        assert resp.status_code == 200
        assert self._find(resp, unlimited_event)["my_rsvp"] is None
