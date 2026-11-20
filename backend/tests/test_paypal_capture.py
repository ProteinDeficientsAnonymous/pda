import pytest
from audit.models import AuditLogEntry
from community.models import Event, EventRSVP
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._paypal_helpers import (
    approved_order,
    completed_capture,
    create_paypal_rsvp,
    mock_paypal,
)

CAPTURE_URL = "/api/community/events/{event_id}/paypal/order/ORDER1/capture/"


@pytest.fixture(autouse=True)
def paypal_settings(settings):
    settings.PAYPAL_CLIENT_ID = "client"
    settings.PAYPAL_CLIENT_SECRET = "secret"


@pytest.fixture
def rsvp(db, test_user):
    return create_paypal_rsvp(test_user)


def _order(rsvp, status="COMPLETED", value="10.87") -> dict:
    capture = completed_capture(rsvp, status, value)
    return {"purchase_units": [{"payments": {"captures": [capture]}}]}


def _paypal(rsvp, order=None, **capture):
    return mock_paypal(_order(rsvp, **capture), order=order or approved_order(rsvp))


def _post(api_client, rsvp, headers):
    return api_client.post(CAPTURE_URL.format(event_id=rsvp.event_id), **headers)


@pytest.mark.django_db
class TestCapture:
    def test_completed_capture_marks_the_rsvp_paid(
        self, api_client, rsvp, auth_headers, django_capture_on_commit_callbacks
    ):
        with _paypal(rsvp) as http, django_capture_on_commit_callbacks(execute=True):
            response = _post(api_client, rsvp, auth_headers)

        assert response.json() == {"paid": True}
        headers = http.call_args.kwargs["headers"]
        assert headers["PayPal-Request-Id"] == "capture-ORDER1"
        assert headers["Prefer"] == "return=representation"
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id == "CAP-1"
        assert rsvp.paid_confirmed_at and rsvp.payment_verified_at
        entry = AuditLogEntry.objects.get(action="guest_payment_changed")
        assert entry.details["source"] == "paypal"
        assert entry.details["payment_verified"] is True

    def test_pending_capture_is_not_paid_yet(self, api_client, rsvp, auth_headers):
        with _paypal(rsvp, status="PENDING"):
            response = _post(api_client, rsvp, auth_headers)

        assert response.json() == {"paid": False}
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id is None

    def test_capture_must_cover_the_price(self, api_client, rsvp, auth_headers):
        with _paypal(rsvp, value="0.01"):
            response = _post(api_client, rsvp, auth_headers)

        assert response.json() == {"paid": False}
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id is None

    @pytest.mark.parametrize(
        "order",
        [
            {"status": "CREATED"},
            {"custom_id": "0"},
            {"value": "0.01"},
            {"currency_code": "EUR"},
        ],
    )
    def test_order_is_checked_before_capturing(self, api_client, rsvp, auth_headers, order):
        approved = approved_order(rsvp, value=order.get("value", "10.87"))
        approved["status"] = order.get("status", "APPROVED")
        unit = approved["purchase_units"][0]
        unit["custom_id"] = order.get("custom_id", unit["custom_id"])
        unit["amount"]["currency_code"] = order.get("currency_code", "USD")
        with _paypal(rsvp, order=approved) as http:
            response = _post(api_client, rsvp, auth_headers)

        assert_error_code(response, Code.Event.PAYPAL_ORDER_INVALID)
        assert http.call_count == 1

    def test_event_must_still_take_paypal(self, api_client, rsvp, auth_headers):
        Event.objects.filter(pk=rsvp.event_id).update(accept_paypal=False)
        with _paypal(rsvp) as http:
            response = _post(api_client, rsvp, auth_headers)

        assert_error_code(response, Code.Event.PAYPAL_NOT_ACCEPTED)
        http.assert_not_called()

    @pytest.mark.parametrize("field", ["payment_verified_at", "paypal_capture_id"])
    def test_paid_rsvp_is_not_charged_again(self, api_client, rsvp, auth_headers, field):
        paid = {"payment_verified_at": timezone.now(), "paypal_capture_id": "CAP-0"}
        EventRSVP.objects.filter(pk=rsvp.pk).update(**{field: paid[field]})
        with _paypal(rsvp) as http:
            response = _post(api_client, rsvp, auth_headers)

        assert_error_code(response, Code.Event.PAYPAL_NOTHING_TO_PAY)
        http.assert_not_called()

    def test_order_id_must_be_alphanumeric(self, api_client, rsvp, auth_headers):
        url = CAPTURE_URL.format(event_id=rsvp.event_id).replace("ORDER1", "bad-id")
        with mock_paypal({}) as http:
            assert api_client.post(url, **auth_headers).status_code == 400
        http.assert_not_called()
