import json
from decimal import ROUND_HALF_UP, Decimal

import pytest
from community.models import Event, EventType
from community.paypal.price import FIXED_FEE, PERCENT_FEE, offered_paypal_price, paypal_price
from community.rsvps.payment import event_requires_payment_confirmation
from community.validation import Code
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._auth import auth_headers_for
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

    def test_fee_inclusive_when_on(self):
        event = build_paid_event(price=Decimal("10"), accept_paypal=True)
        assert offered_paypal_price(event) == Decimal("10.87")


def test_paypal_alone_counts_as_a_payment_method():
    event = build_paid_event(venmo_link="", cashapp_link="", zelle_info="", accept_paypal=True)
    assert event_requires_payment_confirmation(event) is True


@pytest.fixture
def official_headers(db):
    user = User.objects.create_user(phone_number="+14155558888", password="pass12345")
    user.roles.add(
        Role.objects.create(name="official_tagger", permissions=[PermissionKey.TAG_OFFICIAL_EVENT])
    )
    return auth_headers_for(user)


@pytest.mark.django_db
class TestEventPaypalApi:
    def _post(self, api_client, headers, **fields):
        body = {"title": "Dinner", "start_datetime": future_iso(), "price": "10", **fields}
        return api_client.post(
            "/api/community/events/",
            data=json.dumps(body),
            content_type="application/json",
            **headers,
        )

    def _patch(self, api_client, headers, event_id, **fields):
        return api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps(fields),
            content_type="application/json",
            **headers,
        )

    def _official(self, api_client, headers):
        resp = self._post(api_client, headers, event_type=EventType.OFFICIAL, accept_paypal=True)
        assert resp.status_code == 201
        return resp.json()

    def test_paypal_is_off_by_default(self, api_client, auth_headers):
        body = self._post(api_client, auth_headers).json()
        assert (body["accept_paypal"], body["paypal_price"]) == (False, "")

    def test_official_event_returns_the_fee_inclusive_price(self, api_client, official_headers):
        body = self._official(api_client, official_headers)
        assert (body["accept_paypal"], body["paypal_price"]) == (True, "10.87")

    def test_create_rejects_paypal_on_a_community_event(self, api_client, auth_headers):
        resp = self._post(api_client, auth_headers, accept_paypal=True)
        assert resp.status_code == 422
        assert [e["code"] for e in resp.json()["detail"]] == [Code.Event.PAYPAL_OFFICIAL_ONLY]

    def test_patch_rejects_paypal_on_a_community_event(self, api_client, auth_headers):
        event_id = self._post(api_client, auth_headers).json()["id"]
        resp = self._patch(api_client, auth_headers, event_id, accept_paypal=True)
        assert resp.status_code == 422
        assert Event.objects.get(pk=event_id).accept_paypal is False

    def test_patch_turns_paypal_off(self, api_client, official_headers):
        event_id = self._official(api_client, official_headers)["id"]
        resp = self._patch(api_client, official_headers, event_id, accept_paypal=False)
        assert (resp.json()["accept_paypal"], resp.json()["paypal_price"]) == (False, "")

    def test_leaving_official_turns_paypal_off(self, api_client, official_headers):
        event_id = self._official(api_client, official_headers)["id"]
        resp = self._patch(api_client, official_headers, event_id, event_type=EventType.COMMUNITY)
        assert resp.status_code == 200
        assert resp.json()["accept_paypal"] is False
