import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from community.paypal.webhook import MAX_WEBHOOK_BYTES, VERIFY_PATH

from tests._paypal_helpers import completed_capture, create_paypal_rsvp, mock_paypal

WEBHOOK_URL = "/api/community/paypal/webhook/"
SIGNATURE_HEADERS = {
    "HTTP_PAYPAL_AUTH_ALGO": "SHA256withRSA",
    "HTTP_PAYPAL_CERT_URL": "https://api.paypal.com/cert",
    "HTTP_PAYPAL_TRANSMISSION_ID": "tx-1",
    "HTTP_PAYPAL_TRANSMISSION_SIG": "sig",
    "HTTP_PAYPAL_TRANSMISSION_TIME": "2026-11-19T00:00:00Z",
}


@pytest.fixture(autouse=True)
def paypal_settings(settings):
    settings.PAYPAL_CLIENT_ID = "client"
    settings.PAYPAL_CLIENT_SECRET = "secret"
    settings.PAYPAL_WEBHOOK_ID = "WH-1"


@pytest.fixture
def rsvp(db, test_user):
    return create_paypal_rsvp(test_user)


def _deliver(api_client, rsvp, verification="SUCCESS", event_type="PAYMENT.CAPTURE.COMPLETED"):
    event = {
        "id": "WH-EVT",
        "event_type": event_type,
        "resource": completed_capture(rsvp),
    }
    raw = json.dumps(event)
    with mock_paypal({"verification_status": verification}) as http:
        response = api_client.post(
            WEBHOOK_URL, raw, content_type="application/json", **SIGNATURE_HEADERS
        )
    return response, http, raw


@pytest.mark.django_db
class TestWebhook:
    def test_verified_capture_marks_paid_once(self, api_client, rsvp):
        response, http, raw = _deliver(api_client, rsvp)

        assert response.status_code == 200
        body = http.call_args.kwargs["content"]
        assert json.loads(body)["webhook_id"] == "WH-1"
        assert json.loads(body)["transmission_sig"] == "sig"
        assert body.endswith(f'"webhook_event": {raw}}}')
        rsvp.refresh_from_db()
        first_paid_at = rsvp.payment_verified_at
        assert rsvp.paypal_capture_id == "CAP-1"

        assert _deliver(api_client, rsvp)[0].status_code == 200
        rsvp.refresh_from_db()
        assert rsvp.payment_verified_at == first_paid_at

    def test_unverified_webhook_is_rejected(self, api_client, rsvp):
        response, _, _ = _deliver(api_client, rsvp, verification="FAILURE")

        assert response.status_code == 400
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id is None

    def test_non_capture_event_is_acknowledged_without_write(self, api_client, rsvp):
        response, _, _ = _deliver(api_client, rsvp, event_type="PAYMENT.CAPTURE.PENDING")

        assert response.status_code == 200
        rsvp.refresh_from_db()
        assert rsvp.paypal_capture_id is None

    def test_paypal_outage_returns_502(self, api_client, rsvp):
        raw = json.dumps({"event_type": "PAYMENT.CAPTURE.COMPLETED"})
        with patch(
            "community.paypal._client.httpx.post", side_effect=httpx.ConnectError("refused")
        ):
            response = api_client.post(
                WEBHOOK_URL, raw, content_type="application/json", **SIGNATURE_HEADERS
            )
        assert response.status_code == 502

    @pytest.mark.parametrize("body", ["not json", "[]", "{" + " " * MAX_WEBHOOK_BYTES + "}"])
    def test_non_object_body_is_rejected(self, api_client, rsvp, body):
        with mock_paypal({}) as http:
            response = api_client.post(
                WEBHOOK_URL, body, content_type="application/json", **SIGNATURE_HEADERS
            )
        assert response.status_code == 400
        http.assert_not_called()

    def test_missing_signature_header_is_rejected_without_calling_paypal(self, api_client, rsvp):
        headers = {
            k: v for k, v in SIGNATURE_HEADERS.items() if k != "HTTP_PAYPAL_TRANSMISSION_SIG"
        }
        with mock_paypal({}) as http:
            response = api_client.post(
                WEBHOOK_URL, "{}", content_type="application/json", **headers
            )
        assert response.status_code == 400
        http.assert_not_called()

    def test_verify_4xx_is_an_invalid_signature(self, api_client, rsvp):
        request = httpx.Request("POST", f"https://api-m.sandbox.paypal.com{VERIFY_PATH}")
        refused = MagicMock()
        refused.raise_for_status.side_effect = httpx.HTTPStatusError(
            "bad request", request=request, response=httpx.Response(400, request=request)
        )
        token = MagicMock(**{"json.return_value": {"access_token": "token"}})
        with patch("community.paypal._client.httpx.post", side_effect=[token, refused]):
            response = api_client.post(
                WEBHOOK_URL, "{}", content_type="application/json", **SIGNATURE_HEADERS
            )
        assert response.status_code == 400

    def test_unconfigured_webhook_is_unavailable(self, api_client, settings):
        settings.PAYPAL_WEBHOOK_ID = ""
        response = api_client.post(WEBHOOK_URL, "{}", content_type="application/json")
        assert response.status_code == 503
