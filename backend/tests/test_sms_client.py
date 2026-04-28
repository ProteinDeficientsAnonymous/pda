"""Tests for the Twilio SMS client wrapper.

Verifies that ``send_sms`` calls Twilio with the right shape and raises a
clear error when env vars aren't configured. The Twilio client itself is
patched so no real API calls happen.
"""

from unittest.mock import MagicMock, patch

import pytest
from community._sms import get_twilio_client, send_sms


@pytest.fixture(autouse=True)
def _clear_client_cache():
    """Reset the lru_cache between tests so settings overrides take effect."""
    get_twilio_client.cache_clear()
    yield
    get_twilio_client.cache_clear()


def test_send_sms_calls_twilio_with_e164_and_body(settings):
    settings.TWILIO_ACCOUNT_SID = "AC_test"
    settings.TWILIO_AUTH_TOKEN = "tok_test"
    settings.TWILIO_FROM_NUMBER = "+15555550000"

    fake_message = MagicMock()
    fake_message.sid = "SM_fake_sid"
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("community._sms.get_twilio_client", return_value=fake_client):
        sid = send_sms("+15555550100", "hello from pda")

    assert sid == "SM_fake_sid"
    fake_client.messages.create.assert_called_once_with(
        to="+15555550100",
        from_="+15555550000",
        body="hello from pda",
    )


def test_send_sms_raises_when_account_sid_missing(settings):
    settings.TWILIO_ACCOUNT_SID = ""
    settings.TWILIO_AUTH_TOKEN = "tok_test"
    settings.TWILIO_FROM_NUMBER = "+15555550000"

    with pytest.raises(RuntimeError, match="Twilio not configured"):
        send_sms("+15555550100", "hi")


def test_send_sms_raises_when_from_number_missing(settings):
    settings.TWILIO_ACCOUNT_SID = "AC_test"
    settings.TWILIO_AUTH_TOKEN = "tok_test"
    settings.TWILIO_FROM_NUMBER = ""

    with pytest.raises(RuntimeError, match="Twilio not configured"):
        send_sms("+15555550100", "hi")


def test_get_twilio_client_raises_when_not_configured(settings):
    settings.TWILIO_ACCOUNT_SID = ""
    settings.TWILIO_AUTH_TOKEN = ""

    with pytest.raises(RuntimeError, match="Twilio not configured"):
        get_twilio_client()
