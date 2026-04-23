"""Tests for RSVP capacity limits and waitlist behaviour."""

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from users.models import User

from tests.conftest import future_iso

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(phone, name):
    return User.objects.create_user(
        phone_number=phone,
        password="Testpass123!",
        display_name=name,
    )


def _jwt_headers(user):
    from ninja_jwt.tokens import RefreshToken

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

    def test_plus_one_denied_at_capacity(self, api_client, capped_event, headers1, headers2):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        # user1 already attending; tries to add +1 (would exceed capacity)
        resp = _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        assert resp.status_code == 400
        assert "+1" in resp.json()["detail"].lower() or "spots" in resp.json()["detail"].lower()

    def test_waitlisted_has_no_plus_one(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers2, headers3
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3, has_plus_one=True)
        rsvp = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp.status == RSVPStatus.WAITLISTED
        assert rsvp.has_plus_one is False

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
# TestWaitlistPromotion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWaitlistPromotion:
    def test_promote_on_status_change(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers2, headers3
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3)  # waitlisted

        # user1 changes to "maybe" — frees a spot
        _rsvp(api_client, capped_event, headers1, status="maybe")

        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp3.status == RSVPStatus.ATTENDING

    def test_promote_on_delete(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers2, headers3
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3)  # waitlisted

        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)

        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp3.status == RSVPStatus.ATTENDING

    def test_fifo_order(  # noqa: PLR0913
        self,
        api_client,
        capped_event,
        user3,
        user4,
        headers1,
        headers2,
        headers3,
        headers4,
    ):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3)  # waitlisted first
        _rsvp(api_client, capped_event, headers4)  # waitlisted second

        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)

        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        rsvp4 = EventRSVP.objects.get(event=capped_event, user=user4)
        assert rsvp3.status == RSVPStatus.ATTENDING
        assert rsvp4.status == RSVPStatus.WAITLISTED

    def test_promote_multiple_spots(  # noqa: PLR0913
        self,
        api_client,
        capped_event,
        user3,
        user4,
        headers1,
        headers2,
        headers3,
        headers4,
    ):
        # max=2; user1 with +1 fills both spots
        _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        _rsvp(api_client, capped_event, headers3)  # waitlisted
        _rsvp(api_client, capped_event, headers4)  # waitlisted

        # user1 removes +1 → frees 1 spot (still attending, headcount 1)
        _rsvp(api_client, capped_event, headers1, has_plus_one=False)

        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        rsvp4 = EventRSVP.objects.get(event=capped_event, user=user4)
        assert rsvp3.status == RSVPStatus.ATTENDING
        assert rsvp4.status == RSVPStatus.WAITLISTED

    def test_no_promotion_when_no_waitlisted(self, api_client, capped_event, headers1, headers2):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        # Delete one — no waitlisted to promote, should not crash
        resp = api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# TestWaitlistPromotionNotification
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWaitlistPromotionNotification:
    def test_notification_created_on_promote(  # noqa: PLR0913
        self,
        api_client,
        capped_event,
        user3,
        headers1,
        headers2,
        headers3,
    ):
        """Promoted user receives a WAITLIST_PROMOTED notification."""
        from notifications.models import Notification, NotificationType

        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        _rsvp(api_client, capped_event, headers3)  # waitlisted

        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)

        notif = Notification.objects.get(
            recipient=user3,
            notification_type=NotificationType.WAITLIST_PROMOTED,
            event=capped_event,
        )
        assert capped_event.title in notif.message

    def test_no_notification_when_no_waitlisted(self, api_client, capped_event, headers1, headers2):
        """No notification created when a spot frees but nobody is waitlisted."""
        from notifications.models import Notification, NotificationType

        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)

        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)

        assert not Notification.objects.filter(
            notification_type=NotificationType.WAITLIST_PROMOTED,
        ).exists()


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
        from datetime import timedelta

        from django.utils import timezone

        return (timezone.now() + timedelta(days=days)).isoformat()

    def test_create_rejects_zero_max_attendees(self, api_client, auth_headers):
        import json

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
        assert any(e["code"] == "max_attendees_must_be_at_least_one" for e in resp.json()["detail"])

    def test_create_accepts_null_max_attendees(self, api_client, auth_headers):
        import json

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
        import json

        resp = api_client.patch(
            f"/api/community/events/{capped_event.id}/",
            data=json.dumps({"max_attendees": 0}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        assert any(e["code"] == "max_attendees_must_be_at_least_one" for e in resp.json()["detail"])

    def test_patch_accepts_null_max_attendees(self, api_client, capped_event, auth_headers):
        import json

        resp = api_client.patch(
            f"/api/community/events/{capped_event.id}/",
            data=json.dumps({"max_attendees": None}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
