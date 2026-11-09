import json
from decimal import ROUND_HALF_UP, Decimal

import pytest
from community.paypal.price import FIXED_FEE, PERCENT_FEE, offered_paypal_price, paypal_price
from community.rsvps.payment import event_requires_payment_confirmation

from tests._payment_helpers import build_paid_event
from tests._time import future_iso

CENT = Decimal("0.01")


def _net(charge: Decimal) -> Decimal:
    fee = (charge * PERCENT_FEE + FIXED_FEE).quantize(CENT, rounding=ROUND_HALF_UP)
    return charge - fee


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("10", "10.87"), ("20", "21.24"), ("35", "36.78"), ("33.50", "35.22")],
)
def test_paypal_price_matches_the_issue_examples(amount, expected):
    assert paypal_price(Decimal(amount)) == Decimal(expected)


@pytest.mark.parametrize("cents", range(100, 50001, 137))
def test_paypal_price_nets_the_amount_within_a_cent_of_the_minimum(cents):
    amount = Decimal(cents) / 100
    charge = paypal_price(amount)
    assert _net(charge) >= amount
    # Fee rounding can let one cent less still net the amount; the ceiling formula never under-nets.
    assert _net(charge - 2 * CENT) < amount


class TestOfferedPaypalPrice:
    def test_none_unless_paypal_is_on(self):
        assert offered_paypal_price(build_paid_event(price=Decimal("10"))) is None

    def test_none_without_a_price(self):
        assert offered_paypal_price(build_paid_event(price=None, accept_paypal=True)) is None

    def test_plus_one_doubles_the_base_not_the_fee(self):
        event = build_paid_event(price=Decimal("10"), accept_paypal=True)
        assert offered_paypal_price(event, 2) == Decimal("21.24")


def test_paypal_alone_counts_as_a_payment_method():
    event = build_paid_event(venmo_link="", cashapp_link="", zelle_info="", accept_paypal=True)
    assert event_requires_payment_confirmation(event) is True


@pytest.mark.django_db
class TestEventPaypalApi:
    def _create(self, api_client, auth_headers, **fields):
        body = {"title": "Dinner", "start_datetime": future_iso(), **fields}
        resp = api_client.post(
            "/api/community/events/",
            data=json.dumps(body),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 201
        return resp.json()

    def test_paypal_is_off_by_default(self, api_client, auth_headers):
        body = self._create(api_client, auth_headers, price="10")
        assert (body["accept_paypal"], body["paypal_price"]) == (False, "")

    def test_on_with_a_price_returns_fee_inclusive_prices(self, api_client, auth_headers):
        body = self._create(
            api_client, auth_headers, price="10", accept_paypal=True, allow_plus_ones=True
        )
        assert (body["paypal_price"], body["paypal_price_plus_one"]) == ("10.87", "21.24")

    def test_plus_one_price_is_blank_when_plus_ones_are_off(self, api_client, auth_headers):
        body = self._create(api_client, auth_headers, price="10", accept_paypal=True)
        assert (body["paypal_price"], body["paypal_price_plus_one"]) == ("10.87", "")

    def test_patch_turns_paypal_off(self, api_client, auth_headers):
        event_id = self._create(api_client, auth_headers, price="10", accept_paypal=True)["id"]
        resp = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"accept_paypal": False}),
            content_type="application/json",
            **auth_headers,
        )
        assert (resp.json()["accept_paypal"], resp.json()["paypal_price"]) == (False, "")
