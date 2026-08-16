"""Tests for the Brevo bulk sender and the transactional/bulk stream split."""

import logging
from unittest.mock import patch

import httpx
import pytest
from django.conf import settings as django_settings
from notifications import _brevo_sender
from notifications._brevo_sender import BrevoSender
from notifications._console_sender import ConsoleSender
from notifications._resend_sender import ResendSender
from notifications.email_sender import (
    EmailStream,
    get_email_sender,
    reset_email_sender_cache,
)


def _response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json_body if json_body is not None else {},
        request=httpx.Request("POST", _brevo_sender._API_URL),
    )


@pytest.fixture
def brevo_settings(settings):
    settings.BREVO_API_KEY = "test_key"
    settings.BREVO_FROM_EMAIL = "hey@example.com"
    settings.BREVO_FROM_NAME = "pda"
    return settings


class TestBrevoSender:
    def test_send_success_returns_message_id(self, brevo_settings):
        with patch.object(
            httpx.Client, "post", return_value=_response(201, {"messageId": "brevo_abc"})
        ):
            result = BrevoSender().send(
                to="user@example.com", subject="hello", html="<p>hi</p>", text="hi"
            )
        assert result.success is True
        assert result.provider_message_id == "brevo_abc"
        assert result.error is None

    def test_send_posts_expected_payload(self, brevo_settings):
        with patch.object(
            httpx.Client, "post", return_value=_response(201, {"messageId": "m"})
        ) as mock_post:
            BrevoSender().send(to="user@example.com", subject="hello", html="<p>hi</p>", text="hi")
        url = mock_post.call_args.args[0]
        payload = mock_post.call_args.kwargs["json"]
        assert url == _brevo_sender._API_URL
        assert payload["sender"] == {"email": "hey@example.com", "name": "pda"}
        assert payload["to"] == [{"email": "user@example.com"}]
        assert payload["subject"] == "hello"
        assert payload["htmlContent"] == "<p>hi</p>"
        assert payload["textContent"] == "hi"

    def test_sender_name_omitted_when_unset(self, brevo_settings):
        brevo_settings.BREVO_FROM_NAME = ""
        with patch.object(
            httpx.Client, "post", return_value=_response(201, {"messageId": "m"})
        ) as mock_post:
            BrevoSender().send(to="user@example.com", subject="hi", html="<p>x</p>", text="x")
        assert mock_post.call_args.kwargs["json"]["sender"] == {"email": "hey@example.com"}

    def test_api_key_sent_as_header(self, brevo_settings):
        sender = BrevoSender()
        assert sender._client.headers["api-key"] == "test_key"

    def test_send_retries_transient_error_then_succeeds(self, brevo_settings):
        with patch.object(_brevo_sender.time, "sleep"):
            with patch.object(
                httpx.Client,
                "post",
                side_effect=[_response(503), _response(201, {"messageId": "after_retry"})],
            ) as mock_post:
                result = BrevoSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is True
        assert result.provider_message_id == "after_retry"
        assert mock_post.call_count == 2

    def test_send_retries_rate_limit(self, brevo_settings):
        with patch.object(_brevo_sender.time, "sleep"):
            with patch.object(
                httpx.Client,
                "post",
                side_effect=[_response(429), _response(201, {"messageId": "ok"})],
            ) as mock_post:
                result = BrevoSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is True
        assert mock_post.call_count == 2

    def test_send_retries_transport_error(self, brevo_settings):
        with patch.object(_brevo_sender.time, "sleep"):
            with patch.object(
                httpx.Client,
                "post",
                side_effect=[
                    httpx.ConnectTimeout("timed out"),
                    _response(201, {"messageId": "ok"}),
                ],
            ) as mock_post:
                result = BrevoSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is True
        assert mock_post.call_count == 2

    def test_send_does_not_retry_client_error(self, brevo_settings):
        with patch.object(
            httpx.Client, "post", return_value=_response(400, {"code": "invalid_parameter"})
        ) as mock_post:
            result = BrevoSender().send(
                to="user@example.com", subject="hi", html="<p>x</p>", text="x"
            )
        assert result.success is False
        assert mock_post.call_count == 1

    def test_send_gives_up_after_max_attempts(self, brevo_settings):
        with patch.object(_brevo_sender.time, "sleep"):
            with patch.object(httpx.Client, "post", return_value=_response(500)) as mock_post:
                result = BrevoSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is False
        assert mock_post.call_count == _brevo_sender._MAX_ATTEMPTS

    def test_send_reports_failure_for_invalid_recipient_instead_of_raising(self, brevo_settings):
        with patch.object(httpx.Client, "post") as mock_post:
            result = BrevoSender().send(to="not-an-email", subject="hi", html="<p>x</p>", text="x")
        assert result.success is False
        mock_post.assert_not_called()

    def test_send_does_not_log_raw_recipient(self, brevo_settings, caplog):
        with patch.object(httpx.Client, "post", return_value=_response(201, {"messageId": "m"})):
            with caplog.at_level(logging.INFO, logger="notifications.brevo_sender"):
                BrevoSender().send(
                    to="secret.person@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        log_text = "\n".join(r.getMessage() for r in caplog.records)
        assert "secret.person@example.com" not in log_text
        assert "sha256:" in log_text

    def test_failure_does_not_log_raw_recipient(self, brevo_settings, caplog):
        """Brevo's free-text error can echo the address; only the code is logged."""
        body = {"code": "invalid_parameter", "message": "Invalid email: secret.person@example.com"}
        with patch.object(httpx.Client, "post", return_value=_response(400, body)):
            with caplog.at_level(logging.WARNING, logger="notifications.brevo_sender"):
                result = BrevoSender().send(
                    to="secret.person@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is False
        log_text = "\n".join(r.getMessage() for r in caplog.records)
        assert "secret.person@example.com" not in log_text

    def test_success_without_json_body_still_succeeds(self, brevo_settings):
        response = httpx.Response(
            201, content=b"", request=httpx.Request("POST", _brevo_sender._API_URL)
        )
        with patch.object(httpx.Client, "post", return_value=response):
            result = BrevoSender().send(
                to="user@example.com", subject="hi", html="<p>x</p>", text="x"
            )
        assert result.success is True
        assert result.provider_message_id is None


class TestStreamRouting:
    def test_bulk_stream_uses_brevo_when_configured(self, brevo_settings):
        reset_email_sender_cache()
        brevo_settings.RESEND_API_KEY = "resend_key"
        brevo_settings.RESEND_FROM_EMAIL = "noreply@example.com"
        try:
            assert isinstance(get_email_sender(EmailStream.BULK), BrevoSender)
            assert isinstance(get_email_sender(EmailStream.TRANSACTIONAL), ResendSender)
        finally:
            reset_email_sender_cache()

    def test_default_stream_is_transactional(self, brevo_settings):
        reset_email_sender_cache()
        brevo_settings.RESEND_API_KEY = "resend_key"
        brevo_settings.RESEND_FROM_EMAIL = "noreply@example.com"
        try:
            assert get_email_sender() is get_email_sender(EmailStream.TRANSACTIONAL)
        finally:
            reset_email_sender_cache()

    def test_streams_are_cached_independently(self, settings):
        reset_email_sender_cache()
        settings.RESEND_API_KEY = ""
        settings.BREVO_API_KEY = ""
        try:
            bulk = get_email_sender(EmailStream.BULK)
            transactional = get_email_sender(EmailStream.TRANSACTIONAL)
            assert bulk is get_email_sender(EmailStream.BULK)
            assert bulk is not transactional
        finally:
            reset_email_sender_cache()

    def test_bulk_falls_back_to_console_in_dev(self, settings):
        reset_email_sender_cache()
        settings.BREVO_API_KEY = ""
        try:
            assert isinstance(get_email_sender(EmailStream.BULK), ConsoleSender)
        finally:
            reset_email_sender_cache()

    def test_bulk_raises_in_production_without_key(self, monkeypatch):
        """Bulk must never silently fall back onto the transactional provider."""
        reset_email_sender_cache()
        monkeypatch.setattr(django_settings, "BREVO_API_KEY", "")
        monkeypatch.setattr(django_settings, "RESEND_API_KEY", "resend_key")
        monkeypatch.setattr(django_settings, "IS_PRODUCTION", True)
        try:
            with pytest.raises(RuntimeError, match="BREVO_API_KEY"):
                get_email_sender(EmailStream.BULK)
        finally:
            reset_email_sender_cache()
