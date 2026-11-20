import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._payment_helpers import create_eligible_event

ORDER_URL = "/api/community/events/{event_id}/paypal/order/"


def paypal_response(payload: dict) -> MagicMock:
    return MagicMock(**{"json.return_value": payload})


@pytest.fixture(autouse=True)
def paypal_settings(settings):
    settings.PAYPAL_CLIENT_ID = "client"
    settings.PAYPAL_CLIENT_SECRET = "secret"
    settings.PAYPAL_ENV = "sandbox"


@pytest.fixture
def paypal_http():
    with patch("community.paypal._client.httpx.post") as post:
        post.side_effect = [
            paypal_response({"access_token": "token"}),
            paypal_response({"id": "ORDER-1"}),
        ]
        yield post


@pytest.fixture
def event(db, test_user):
    return create_eligible_event(created_by=test_user, accept_paypal=True, price=Decimal("10"))


@pytest.fixture
def rsvp(event, test_user):
    return EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)


def _post(api_client, event, headers):
    return api_client.post(ORDER_URL.format(event_id=event.id), **headers)


@pytest.mark.django_db
class TestCreatePayPalOrder:
    def test_creates_order_for_the_fee_inclusive_price(
        self, api_client, paypal_http, event, rsvp, auth_headers
    ):
        response = _post(api_client, event, auth_headers)

        assert response.status_code == 200
        assert response.json() == {"order_id": "ORDER-1", "amount": "10.87"}
        token_call, order_call = paypal_http.call_args_list
        assert token_call.args[0] == "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        assert order_call.kwargs["headers"]["Authorization"] == "Bearer token"
        unit = json.loads(order_call.kwargs["content"])["purchase_units"][0]
        assert unit["custom_id"] == str(rsvp.pk)
        assert unit["amount"] == {"currency_code": "USD", "value": "10.87"}

    def test_unconfigured_paypal_is_unavailable(
        self, api_client, settings, paypal_http, event, rsvp, auth_headers
    ):
        settings.PAYPAL_CLIENT_ID = ""
        assert _post(api_client, event, auth_headers).status_code == 503
        paypal_http.assert_not_called()

    @pytest.mark.parametrize(
        "fields",
        [{"accept_paypal": False}, {"price": None}, {"status": EventStatus.CANCELLED}],
    )
    def test_event_must_take_paypal(
        self, api_client, paypal_http, event, rsvp, auth_headers, fields
    ):
        Event.objects.filter(pk=event.pk).update(**fields)
        response = _post(api_client, event, auth_headers)
        assert_error_code(response, Code.Event.PAYPAL_NOT_ACCEPTED)
        paypal_http.assert_not_called()

    @pytest.mark.parametrize(
        "fields",
        [None, {"status": RSVPStatus.CANT_GO}, {"payment_verified_at": timezone.now()}],
    )
    def test_rsvp_must_still_need_payment(
        self, api_client, paypal_http, event, rsvp, auth_headers, fields
    ):
        rows = EventRSVP.objects.filter(pk=rsvp.pk)
        if fields:
            rows.update(**fields)
        else:
            rows.delete()
        response = _post(api_client, event, auth_headers)
        assert_error_code(response, Code.Event.PAYPAL_NOTHING_TO_PAY)
        paypal_http.assert_not_called()

    def test_paypal_failure_is_a_bad_gateway(
        self, api_client, paypal_http, event, rsvp, auth_headers
    ):
        paypal_http.side_effect = httpx.ConnectError("refused")
        assert _post(api_client, event, auth_headers).status_code == 502
