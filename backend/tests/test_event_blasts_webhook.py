"""Tests for the inbound Twilio webhook (issue #403).

Split from `test_event_blasts.py` to keep both files under the 500-line cap.
The webhook is signature-validated against TWILIO_AUTH_TOKEN; tests forge a
real signature using `RequestValidator.compute_signature`.
"""

import pytest
from community.models import EventBlastMute

from tests._event_blasts_shared import TEST_TWILIO_TOKEN, TEST_WEBHOOK_URL, send_blast


def _twilio_signed_request(api_client, params: dict):
    """Forge a valid Twilio signature against the test settings."""
    from twilio.request_validator import RequestValidator

    validator = RequestValidator(TEST_TWILIO_TOKEN)
    signature = validator.compute_signature(TEST_WEBHOOK_URL, params)
    return api_client.post(
        "/api/community/twilio/inbound/",
        data=params,
        HTTP_X_TWILIO_SIGNATURE=signature,
    )


@pytest.mark.django_db
class TestInboundWebhook:
    def test_m_creates_mute_for_most_recent_event(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="x",
            recipient_filters=["attending"],
        )
        response = _twilio_signed_request(
            api_client,
            {"From": attendee.phone_number, "Body": "M"},
        )
        assert response.status_code == 200
        assert "you're muted" in response.content.decode().lower()
        assert EventBlastMute.objects.filter(event=event_with_attendees, user=attendee).exists()

    def test_m_case_insensitive(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="x",
            recipient_filters=["attending"],
        )
        for body in [" m ", "m", "M"]:
            EventBlastMute.objects.filter(event=event_with_attendees, user=attendee).delete()
            response = _twilio_signed_request(
                api_client,
                {"From": attendee.phone_number, "Body": body},
            )
            assert response.status_code == 200
            assert EventBlastMute.objects.filter(event=event_with_attendees, user=attendee).exists()

    def test_unknown_phone_returns_empty_twiml(self, api_client):
        response = _twilio_signed_request(
            api_client,
            {"From": "+19995550100", "Body": "M"},
        )
        assert response.status_code == 200
        assert response.content.decode().strip() == "<Response/>"

    def test_non_m_body_returns_empty_twiml(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="x",
            recipient_filters=["attending"],
        )
        response = _twilio_signed_request(
            api_client,
            {"From": attendee.phone_number, "Body": "thanks!"},
        )
        assert response.status_code == 200
        assert response.content.decode().strip() == "<Response/>"
        # No mute created.
        assert not EventBlastMute.objects.filter(event=event_with_attendees, user=attendee).exists()

    def test_invalid_signature_returns_403(self, api_client):
        response = api_client.post(
            "/api/community/twilio/inbound/",
            data={"From": "+15555550000", "Body": "M"},
            HTTP_X_TWILIO_SIGNATURE="forged",
        )
        assert response.status_code == 403

    def test_idempotent_double_m(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="x",
            recipient_filters=["attending"],
        )
        for _ in range(2):
            _twilio_signed_request(
                api_client,
                {"From": attendee.phone_number, "Body": "M"},
            )
        assert EventBlastMute.objects.filter(event=event_with_attendees, user=attendee).count() == 1
