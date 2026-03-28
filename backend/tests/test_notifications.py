import json
import urllib.error
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from notifications.service import admin_broadcast, notify_new_event
from notifications.whatsapp import send_to_group


@pytest.fixture
def configured_settings(settings):
    settings.WHATSAPP_BOT_URL = "http://localhost:3001"
    settings.WHATSAPP_BOT_SECRET = "test-secret"
    settings.WHATSAPP_GROUP_ID = "1234567890@g.us"
    return settings


@pytest.fixture
def unconfigured_settings(settings):
    settings.WHATSAPP_BOT_URL = ""
    settings.WHATSAPP_GROUP_ID = ""
    return settings


def _make_urlopen_response(status=200, body=b'{"ok":true}'):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestSendToGroup:
    def test_sends_message_when_configured(self, configured_settings):
        mock_resp = _make_urlopen_response()

        with patch(
            "notifications.whatsapp.urllib.request.urlopen", return_value=mock_resp
        ) as mock_open:
            result = send_to_group("Hello group!")

        assert result is True
        req = mock_open.call_args[0][0]
        assert req.get_method() == "POST"
        assert "send" in req.full_url
        assert req.get_header("X-bot-secret") == "test-secret"
        body = json.loads(req.data)
        assert body["groupId"] == "1234567890@g.us"
        assert body["message"] == "Hello group!"

    def test_returns_false_when_not_configured(self, unconfigured_settings):
        with patch("notifications.whatsapp.urllib.request.urlopen") as mock_open:
            result = send_to_group("Hello group!")

        assert result is False
        mock_open.assert_not_called()

    def test_returns_false_on_url_error(self, configured_settings):
        with patch(
            "notifications.whatsapp.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            result = send_to_group("Hello group!")

        assert result is False

    def test_returns_false_on_http_error(self, configured_settings):
        with patch(
            "notifications.whatsapp.urllib.request.urlopen",
            side_effect=OSError("HTTP Error 503"),
        ):
            result = send_to_group("Hello group!")

        assert result is False


class TestNotifyNewEvent:
    def _make_event(self, **kwargs):
        event = MagicMock()
        event.title = kwargs.get("title", "Test Event")
        event.description = kwargs.get("description", "")
        event.location = kwargs.get("location", "")
        event.partiful_link = kwargs.get("partiful_link", "")
        event.whatsapp_link = kwargs.get("whatsapp_link", "")
        event.other_link = kwargs.get("other_link", "")
        event.start_datetime = kwargs.get(
            "start_datetime", datetime(2026, 4, 15, 19, 0, tzinfo=UTC)
        )
        event.end_datetime = kwargs.get("end_datetime", datetime(2026, 4, 15, 21, 0, tzinfo=UTC))
        return event

    def test_sends_event_notification(self, configured_settings):
        event = self._make_event(
            title="Potluck", location="123 Main St", partiful_link="https://partiful.com/e/abc"
        )

        with patch("notifications.service.send_to_group", return_value=True) as mock_send:
            result = notify_new_event(event)

        assert result is True
        message = mock_send.call_args[0][0]
        assert "Potluck" in message
        assert "123 Main St" in message
        assert "https://partiful.com/e/abc" in message

    def test_omits_empty_fields(self, configured_settings):
        event = self._make_event(title="Simple Event")

        with patch("notifications.service.send_to_group", return_value=True) as mock_send:
            notify_new_event(event)

        message = mock_send.call_args[0][0]
        assert "📍" not in message

    def test_falls_back_to_whatsapp_link(self, configured_settings):
        event = self._make_event(whatsapp_link="https://chat.whatsapp.com/abc")

        with patch("notifications.service.send_to_group", return_value=True) as mock_send:
            notify_new_event(event)

        message = mock_send.call_args[0][0]
        assert "https://chat.whatsapp.com/abc" in message


class TestAdminBroadcast:
    def test_broadcasts_message(self, configured_settings):
        with patch("notifications.service.send_to_group", return_value=True) as mock_send:
            result = admin_broadcast("Important announcement!")

        assert result is True
        mock_send.assert_called_once_with("Important announcement!")
