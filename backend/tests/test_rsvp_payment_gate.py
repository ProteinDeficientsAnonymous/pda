"""Tests for the payment-confirmation gate helpers and RSVP enforcement."""

import pytest
from community._rsvp_payment import (
    event_requires_payment_confirmation,
    requires_payment_gate,
)
from community.models import (
    Event,
    EventRSVP,
    FeatureFlag,
    FeatureFlagState,
    RSVPStatus,
)

from tests.conftest import future_iso

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
