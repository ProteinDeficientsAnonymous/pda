"""Tests for the payment-confirmation gate helpers and RSVP enforcement."""

import pytest
from community._rsvp_payment import (
    event_requires_payment_confirmation,
    requires_payment_gate,
)
from community._validation import Code
from community.models import (
    Event,
    EventRSVP,
    EventStatus,
    FeatureFlag,
    FeatureFlagState,
    PageVisibility,
    RSVPStatus,
)

from users.models import NonMemberRsvpToken

from tests._asserts import assert_error_code
from tests._public_rsvp_helpers import make_non_member, make_official_event
from tests._public_rsvp_helpers import payload as public_payload
from tests._public_rsvp_helpers import url as public_url
from tests.conftest import future_iso

RSVP_URL = "/api/community/events/{event_id}/rsvp/"

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


@pytest.fixture(autouse=True)
def _flag_on(db):
    """Every test in this module exercises flag-ON behavior.

    Flag-OFF behavior is covered by test_payment_confirmation_flag_off.py.
    """
    FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})


def make_event(**overrides) -> Event:
    base = {
        "title": "Paid Event",
        "start_datetime": future_iso(days=10),
        "end_datetime": future_iso(days=10, hours=2),
        "rsvp_enabled": True,
        "price": "$10",
        "venmo_link": "https://venmo.com/u/host",
    }
    base.update(overrides)
    return Event(**base)


class TestEventRequiresPaymentConfirmation:
    def test_price_plus_venmo_requires_confirmation(self):
        assert event_requires_payment_confirmation(make_event()) is True

    def test_price_plus_cashapp_requires_confirmation(self):
        event = make_event(venmo_link="", cashapp_link="https://cash.app/$host")
        assert event_requires_payment_confirmation(event) is True

    def test_price_plus_zelle_requires_confirmation(self):
        event = make_event(venmo_link="", zelle_info="host@example.com")
        assert event_requires_payment_confirmation(event) is True

    def test_price_with_no_payment_method_does_not_require(self):
        assert event_requires_payment_confirmation(make_event(venmo_link="")) is False

    def test_payment_method_with_no_price_does_not_require(self):
        assert event_requires_payment_confirmation(make_event(price="")) is False

    def test_blank_price_whitespace_does_not_require(self):
        assert event_requires_payment_confirmation(make_event(price="   ")) is False

    def test_free_event_does_not_require(self):
        event = make_event(price="", venmo_link="", cashapp_link="", zelle_info="")
        assert event_requires_payment_confirmation(event) is False


@pytest.mark.django_db
class TestRequiresPaymentGate:
    def test_new_attending_rsvp_gates(self):
        assert requires_payment_gate(make_event(), None, RSVPStatus.ATTENDING) is True

    def test_new_maybe_rsvp_does_not_gate(self):
        assert requires_payment_gate(make_event(), None, RSVPStatus.MAYBE) is False

    def test_new_cant_go_rsvp_does_not_gate(self):
        assert requires_payment_gate(make_event(), None, RSVPStatus.CANT_GO) is False

    def test_maybe_to_attending_gates(self):
        existing = EventRSVP(status=RSVPStatus.MAYBE)
        assert requires_payment_gate(make_event(), existing, RSVPStatus.ATTENDING) is True

    def test_already_attending_does_not_regate(self):
        existing = EventRSVP(status=RSVPStatus.ATTENDING)
        assert requires_payment_gate(make_event(), existing, RSVPStatus.ATTENDING) is False

    def test_already_confirmed_does_not_regate(self):
        existing = EventRSVP(status=RSVPStatus.MAYBE, paid_confirmed_at=future_iso(days=0))
        assert requires_payment_gate(make_event(), existing, RSVPStatus.ATTENDING) is False

    def test_free_event_never_gates(self):
        free = make_event(price="", venmo_link="")
        assert requires_payment_gate(free, None, RSVPStatus.ATTENDING) is False

    def test_flag_off_never_gates(self):
        FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": False})
        assert requires_payment_gate(make_event(), None, RSVPStatus.ATTENDING) is False


@pytest.fixture
def paid_event(db, test_user):
    return Event.objects.create(
        title="Paid Event",
        start_datetime=future_iso(days=10),
        end_datetime=future_iso(days=10, hours=2),
        rsvp_enabled=True,
        status=EventStatus.ACTIVE,
        visibility=PageVisibility.PUBLIC,
        price="$10",
        venmo_link="https://venmo.com/u/host",
        created_by=test_user,
    )


@pytest.mark.django_db
class TestMemberRsvpPaymentGate:
    def test_attending_without_confirmation_is_rejected(self, api_client, paid_event, auth_headers):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)
        assert not EventRSVP.objects.filter(event=paid_event).exists()

    def test_attending_with_confirmation_succeeds_and_stamps(
        self, api_client, paid_event, auth_headers
    ):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=paid_event)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is not None

    def test_maybe_without_confirmation_succeeds(self, api_client, paid_event, auth_headers):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.MAYBE, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=paid_event).paid_confirmed_at is None

    def test_already_attending_can_toggle_plus_one_without_confirmation(
        self, api_client, paid_event, auth_headers, test_user
    ):
        paid_event.allow_plus_ones = True
        paid_event.save(update_fields=["allow_plus_ones"])
        EventRSVP.objects.create(event=paid_event, user=test_user, status=RSVPStatus.ATTENDING)
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_confirmation_persists_across_later_status_changes(
        self, api_client, paid_event, auth_headers
    ):
        api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        stamped = EventRSVP.objects.get(event=paid_event).paid_confirmed_at
        api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.MAYBE, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=paid_event).paid_confirmed_at == stamped

    def test_free_event_needs_no_confirmation(self, api_client, paid_event, auth_headers):
        paid_event.price = ""
        paid_event.venmo_link = ""
        paid_event.save(update_fields=["price", "venmo_link"])
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200


@pytest.fixture
def paid_public_event(db):
    return make_official_event(
        title="Paid Official Event",
        price="$10",
        venmo_link="https://venmo.com/u/host",
    )


@pytest.mark.django_db
class TestPublicSubmitPaymentGate:
    def test_new_person_attending_without_confirmation_is_rejected(
        self, api_client, paid_public_event
    ):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.ATTENDING),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_new_person_attending_with_confirmation_succeeds(self, api_client, paid_public_event):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.ATTENDING, paid_confirmed=True),
            content_type="application/json",
        )
        assert response.status_code in (200, 201)
        assert EventRSVP.objects.get(event=paid_public_event).paid_confirmed_at is not None

    def test_new_person_maybe_needs_no_confirmation(self, api_client, paid_public_event):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.MAYBE),
            content_type="application/json",
        )
        assert response.status_code in (200, 201)


@pytest.mark.django_db
class TestPublicManagePaymentGate:
    def _setup(self, event, phone="+14155550199"):
        user = make_non_member(phone, "token@example.com", name="Token Holder")
        EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.MAYBE)
        return user, NonMemberRsvpToken.issue_or_extend(user).token

    def test_maybe_to_attending_without_confirmation_is_rejected(
        self, api_client, paid_public_event
    ):
        _user, token = self._setup(paid_public_event)
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_maybe_to_attending_with_confirmation_succeeds(self, api_client, paid_public_event):
        user, token = self._setup(paid_public_event, phone="+14155550198")
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=paid_public_event, user=user)
        assert rsvp.paid_confirmed_at is not None

    def test_switching_to_maybe_needs_no_confirmation(self, api_client, paid_public_event):
        user = make_non_member("+14155550197", "t2@example.com", name="Token Two")
        EventRSVP.objects.create(event=paid_public_event, user=user, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(user).token
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
        )
        assert response.status_code == 200
