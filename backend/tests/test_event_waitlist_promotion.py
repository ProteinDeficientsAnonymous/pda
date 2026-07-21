"""Tests for waitlist promotion behaviour when RSVP capacity frees up."""

import pytest
from community._event_helpers import promote_from_waitlist
from community.models import Event, EventRSVP, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
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


def _rsvp(api_client, event, headers, status="attending", has_plus_one=False):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status, "has_plus_one": has_plus_one},
        content_type="application/json",
        **headers,
    )


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

    def test_waitlisted_plus_one_party_promoted_together(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers3
    ):
        # max=2; user1 with +1 fills both seats. user3 requests attending +1
        # (a party of 2) → waitlisted whole, +1 kept — never seated solo.
        _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        _rsvp(api_client, capped_event, headers3, has_plus_one=True)
        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp3.status == RSVPStatus.WAITLISTED
        assert rsvp3.has_plus_one is True

        # user1 fully cancels → both seats free → user3's party seated together.
        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)
        rsvp3.refresh_from_db()
        assert rsvp3.status == RSVPStatus.ATTENDING
        assert rsvp3.has_plus_one is True

    def test_waitlisted_plus_one_party_not_seated_solo_into_one_seat(  # noqa: PLR0913
        self, api_client, capped_event, user3, headers1, headers3
    ):
        # Only one seat frees up — the +1 party must wait, not be seated solo.
        _rsvp(api_client, capped_event, headers1, has_plus_one=True)
        _rsvp(api_client, capped_event, headers3, has_plus_one=True)  # waitlisted party of 2

        # user1 drops just their +1 → exactly 1 seat opens.
        _rsvp(api_client, capped_event, headers1, has_plus_one=False)
        rsvp3 = EventRSVP.objects.get(event=capped_event, user=user3)
        assert rsvp3.status == RSVPStatus.WAITLISTED
        assert rsvp3.has_plus_one is True

    def test_no_promotion_when_no_waitlisted(self, api_client, capped_event, headers1, headers2):
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)
        # Delete one — no waitlisted to promote, should not crash
        resp = api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)
        assert resp.status_code == 204

    def test_waitlisted_plus_one_not_promoted_into_single_seat(self, test_user, user2):
        """A WAITLISTED +1 row, unreachable via the API but forced here, must not overfill."""
        event = Event.objects.create(
            title="Single Seat Event",
            start_datetime=future_iso(days=30),
            rsvp_enabled=True,
            max_attendees=1,
            allow_plus_ones=True,
            created_by=test_user,
        )
        EventRSVP.objects.create(
            event=event,
            user=user2,
            status=RSVPStatus.WAITLISTED,
            has_plus_one=True,
        )

        promote_from_waitlist(event)

        headcount = sum(
            1 + (1 if r.has_plus_one else 0)
            for r in EventRSVP.objects.filter(event=event, status=RSVPStatus.ATTENDING)
        )
        assert headcount <= event.max_attendees
        rsvp2 = EventRSVP.objects.get(event=event, user=user2)
        assert rsvp2.status == RSVPStatus.WAITLISTED


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
        _rsvp(api_client, capped_event, headers1)
        _rsvp(api_client, capped_event, headers2)

        api_client.delete(f"/api/community/events/{capped_event.id}/rsvp/", **headers1)

        assert not Notification.objects.filter(
            notification_type=NotificationType.WAITLIST_PROMOTED,
        ).exists()
