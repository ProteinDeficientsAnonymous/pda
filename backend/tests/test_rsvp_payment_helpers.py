"""Tests for the payment-confirmation helper predicates."""

import pytest
from community._rsvp_payment import (
    can_see_payment_details,
    event_requires_payment_confirmation,
    payment_enforced_for_event,
    requires_payment_gate,
)
from community.models import EventRSVP, EventType, RSVPStatus
from django.utils import timezone

from tests._payment_helpers import (
    build_eligible_event,
    build_paid_event,
    set_payment_flag,
)


@pytest.fixture(autouse=True)
def _flag_on(db):
    """Flag-OFF behavior is covered by test_payment_confirmation_flag_off.py."""
    set_payment_flag(True)


class TestEventRequiresPaymentConfirmation:
    def test_price_plus_venmo_requires_confirmation(self):
        assert event_requires_payment_confirmation(build_paid_event()) is True

    def test_price_plus_cashapp_requires_confirmation(self):
        event = build_paid_event(venmo_link="", cashapp_link="https://cash.app/$host")
        assert event_requires_payment_confirmation(event) is True

    def test_price_plus_zelle_requires_confirmation(self):
        event = build_paid_event(venmo_link="", zelle_info="host@example.com")
        assert event_requires_payment_confirmation(event) is True

    def test_price_with_no_payment_method_does_not_require(self):
        assert event_requires_payment_confirmation(build_paid_event(venmo_link="")) is False

    def test_payment_method_with_no_price_does_not_require(self):
        assert event_requires_payment_confirmation(build_paid_event(price="")) is False

    def test_blank_price_whitespace_does_not_require(self):
        assert event_requires_payment_confirmation(build_paid_event(price="   ")) is False

    def test_free_event_does_not_require(self):
        event = build_paid_event(price="", venmo_link="", cashapp_link="", zelle_info="")
        assert event_requires_payment_confirmation(event) is False


@pytest.mark.django_db
class TestRequiresPaymentGate:
    def test_new_attending_rsvp_gates(self):
        assert requires_payment_gate(build_paid_event(), None, RSVPStatus.ATTENDING) is True

    def test_new_maybe_rsvp_does_not_gate(self):
        assert requires_payment_gate(build_paid_event(), None, RSVPStatus.MAYBE) is False

    def test_new_cant_go_rsvp_does_not_gate(self):
        assert requires_payment_gate(build_paid_event(), None, RSVPStatus.CANT_GO) is False

    def test_maybe_to_attending_gates(self):
        existing = EventRSVP(status=RSVPStatus.MAYBE)
        assert requires_payment_gate(build_paid_event(), existing, RSVPStatus.ATTENDING) is True

    def test_attending_but_unconfirmed_still_gates(self):
        """Waitlist promotion seats a row as attending without a confirmation, so
        attending is not proof of payment."""
        existing = EventRSVP(status=RSVPStatus.ATTENDING)
        assert requires_payment_gate(build_paid_event(), existing, RSVPStatus.ATTENDING) is True

    def test_already_confirmed_does_not_regate(self):
        existing = EventRSVP(status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now())
        assert requires_payment_gate(build_paid_event(), existing, RSVPStatus.ATTENDING) is False

    def test_confirmed_on_earlier_status_does_not_regate(self):
        existing = EventRSVP(status=RSVPStatus.MAYBE, paid_confirmed_at=timezone.now())
        assert requires_payment_gate(build_paid_event(), existing, RSVPStatus.ATTENDING) is False

    def test_free_event_never_gates(self):
        free = build_paid_event(price="", venmo_link="")
        assert requires_payment_gate(free, None, RSVPStatus.ATTENDING) is False

    def test_flag_off_never_gates(self):
        set_payment_flag(False)
        assert requires_payment_gate(build_paid_event(), None, RSVPStatus.ATTENDING) is False


@pytest.mark.django_db
class TestPaymentEnforcedForEvent:
    def test_paid_event_needs_payment(self):
        assert payment_enforced_for_event(build_paid_event()) is True

    def test_free_event_does_not(self):
        assert payment_enforced_for_event(build_paid_event(price="")) is False

    def test_flag_off_does_not(self):
        set_payment_flag(False)
        assert payment_enforced_for_event(build_paid_event()) is False


@pytest.mark.django_db
class TestCanSeePaymentDetails:
    def test_authed_viewer_always_sees(self):
        assert can_see_payment_details(build_paid_event(), is_authed=True) is True

    def test_anon_sees_on_public_rsvp_eligible_paid_event(self):
        assert can_see_payment_details(build_eligible_event(), is_authed=False) is True

    def test_anon_does_not_see_on_ineligible_event(self):
        community = build_eligible_event(event_type=EventType.COMMUNITY)
        assert can_see_payment_details(community, is_authed=False) is False

    def test_anon_does_not_see_on_free_event(self):
        free = build_eligible_event(price="", venmo_link="")
        assert can_see_payment_details(free, is_authed=False) is False

    def test_visibility_does_not_depend_on_the_gate_flag(self):
        """The flag governs whether payment is enforced, not who may see the cost."""
        set_payment_flag(False)
        assert can_see_payment_details(build_eligible_event(), is_authed=False) is True
        assert can_see_payment_details(build_eligible_event(), is_authed=True) is True

    def test_needs_no_query(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            assert can_see_payment_details(build_eligible_event(), is_authed=False) is True
