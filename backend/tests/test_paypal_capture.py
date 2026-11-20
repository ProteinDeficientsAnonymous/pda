import pytest
from audit.models import AuditLogEntry
from community.models import EventRSVP
from community.validation import Code
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._paypal_helpers import completed_capture, create_paypal_rsvp, mock_paypal

CAPTURE_URL = "/api/community/events/{event_id}/paypal/order/ORDER1/capture/"


@pytest.fixture(autouse=True)
def paypal_settings(settings):
    settings.PAYPAL_CLIENT_ID = "client"
    settings.PAYPAL_CLIENT_SECRET = "secret"


@pytest.fixture
def rsvp(db, test_user):
    return create_paypal_rsvp(test_user)


def _order(rsvp, status="COMPLETED") -> dict:
    return {"purchase_units": [{"payments": {"captures": [completed_capture(rsvp, status)]}}]}


def _post(api_client, rsvp, headers):
    return api_client.post(CAPTURE_URL.format(event_id=rsvp.event_id), **headers)


@pytest.mark.django_db
class TestCapture:
    def test_completed_capture_marks_the_rsvp_paid(
        self, api_client, rsvp, auth_headers, django_capture_on_commit_callbacks
    ):
        with mock_paypal(_order(rsvp)) as http, django_capture_on_commit_callbacks(execute=True):
            response = _post(api_client, rsvp, auth_headers)

        assert response.json() == {"paid": True}
        assert http.call_args.kwargs["headers"]["PayPal-Request-Id"] == "capture-ORDER1"
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id == "CAP-1"
        assert rsvp.paid_confirmed_at and rsvp.payment_verified_at
        entry = AuditLogEntry.objects.get(action="guest_payment_changed")
        assert entry.details["source"] == "paypal"
        assert entry.details["payment_verified"] is True

    def test_pending_capture_is_not_paid_yet(self, api_client, rsvp, auth_headers):
        with mock_paypal(_order(rsvp, status="PENDING")):
            response = _post(api_client, rsvp, auth_headers)

        assert response.json() == {"paid": False}
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id is None

    @pytest.mark.parametrize("field", ["payment_verified_at", "paypal_capture_id"])
    def test_paid_rsvp_is_not_charged_again(self, api_client, rsvp, auth_headers, field):
        paid = {"payment_verified_at": timezone.now(), "paypal_capture_id": "CAP-0"}
        EventRSVP.objects.filter(pk=rsvp.pk).update(**{field: paid[field]})
        with mock_paypal(_order(rsvp)) as http:
            response = _post(api_client, rsvp, auth_headers)

        assert_error_code(response, Code.Event.PAYPAL_NOTHING_TO_PAY)
        http.assert_not_called()

    def test_order_id_must_be_alphanumeric(self, api_client, rsvp, auth_headers):
        url = CAPTURE_URL.format(event_id=rsvp.event_id).replace("ORDER1", "bad-id")
        with mock_paypal({}) as http:
            assert api_client.post(url, **auth_headers).status_code == 400
        http.assert_not_called()
