"""Tests for the email sender protocol and SendResult dataclass."""

import logging
from unittest.mock import patch

import pytest
from notifications.email_sender import EmailSender, SendResult


class TestSendResult:
    def test_default_is_failure(self):
        result = SendResult(success=False)
        assert result.success is False
        assert result.provider_message_id is None
        assert result.error is None

    def test_success_with_message_id(self):
        result = SendResult(success=True, provider_message_id="msg_123")
        assert result.success is True
        assert result.provider_message_id == "msg_123"
        assert result.error is None

    def test_failure_with_error(self):
        result = SendResult(success=False, error="invalid recipient")
        assert result.success is False
        assert result.error == "invalid recipient"


class TestEmailSenderProtocol:
    def test_protocol_signature(self):
        class FakeSender:
            def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
                return SendResult(success=True)

        assert isinstance(FakeSender(), EmailSender)


class TestConsoleSender:
    def test_send_returns_success(self):
        from notifications._console_sender import ConsoleSender

        sender = ConsoleSender()
        result = sender.send(
            to="user@example.com",
            subject="hello",
            html="<p>hi</p>",
            text="hi",
        )
        assert result.success is True
        assert result.error is None

    def test_send_logs_email(self, caplog):
        import logging

        from notifications._console_sender import ConsoleSender

        with caplog.at_level(logging.INFO, logger="notifications.console_sender"):
            ConsoleSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        # Verify the log captured the recipient and subject
        log_text = "\n".join(r.message for r in caplog.records)
        assert "user@example.com" in log_text
        assert "hello" in log_text


class TestResendSender:
    def test_send_success_returns_message_id(self):
        from notifications._resend_sender import ResendSender

        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_abc123"}
            result = ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        assert result.success is True
        assert result.provider_message_id == "msg_abc123"
        assert result.error is None

    def test_send_exception_returns_failure(self):
        from notifications._resend_sender import ResendSender

        with patch("resend.Emails.send", side_effect=RuntimeError("boom")):
            result = ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        assert result.success is False
        assert result.provider_message_id is None
        assert "boom" in (result.error or "")

    def test_send_does_not_log_raw_recipient(self, caplog):
        from notifications._resend_sender import ResendSender

        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_abc123"}
            with caplog.at_level(logging.INFO, logger="notifications.resend_sender"):
                ResendSender().send(
                    to="secret.person@example.com",
                    subject="hello",
                    html="<p>hi</p>",
                    text="hi",
                )
        log_text = "\n".join(r.getMessage() for r in caplog.records)
        # PII (the raw recipient) must never appear in logs.
        assert "secret.person@example.com" not in log_text
        # A masked, non-reversible token is logged for correlation instead.
        assert "sha256:" in log_text
        assert "msg_abc123" in log_text

    def test_send_failure_does_not_log_raw_recipient(self, caplog):
        from notifications._resend_sender import ResendSender
        from resend.exceptions import ResendError

        err = ResendError(
            code="400",
            error_type="validation_error",
            message="bad",
            suggested_action="",
        )
        with patch("resend.Emails.send", side_effect=err):
            with caplog.at_level(logging.WARNING, logger="notifications.resend_sender"):
                result = ResendSender().send(
                    to="secret.person@example.com",
                    subject="hello",
                    html="<p>hi</p>",
                    text="hi",
                )
        assert result.success is False
        log_text = "\n".join(r.getMessage() for r in caplog.records)
        assert "secret.person@example.com" not in log_text

    def test_send_retries_transient_error_then_succeeds(self):
        from notifications import _resend_sender
        from notifications._resend_sender import ResendSender
        from resend.exceptions import RateLimitError

        transient = RateLimitError(
            code="429", error_type="rate_limit_exceeded", message="slow down"
        )
        with patch.object(_resend_sender.time, "sleep"):
            with patch(
                "resend.Emails.send",
                side_effect=[transient, {"id": "msg_after_retry"}],
            ) as mock_send:
                result = ResendSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is True
        assert result.provider_message_id == "msg_after_retry"
        assert mock_send.call_count == 2

    def test_send_does_not_retry_client_error(self):
        from notifications._resend_sender import ResendSender
        from resend.exceptions import ValidationError

        err = ValidationError(code="400", error_type="validation_error", message="bad")
        with patch("resend.Emails.send", side_effect=err) as mock_send:
            result = ResendSender().send(
                to="user@example.com", subject="hi", html="<p>x</p>", text="x"
            )
        assert result.success is False
        # 4xx (other than 429) is not transient → no retry.
        assert mock_send.call_count == 1

    def test_failure_log_reports_true_attempt_count(self, caplog):
        """A non-retryable error breaks after one try; the log must say attempts=1."""
        from notifications._resend_sender import ResendSender
        from resend.exceptions import ValidationError

        err = ValidationError(code="400", error_type="validation_error", message="bad")
        with patch("resend.Emails.send", side_effect=err):
            with caplog.at_level(logging.WARNING, logger="notifications.resend_sender"):
                ResendSender().send(to="user@example.com", subject="hi", html="<p>x</p>", text="x")
        failure_logs = [
            r.getMessage() for r in caplog.records if "resend_send_failure" in r.getMessage()
        ]
        assert failure_logs
        assert "attempts=1" in failure_logs[0]

    def test_send_gives_up_after_max_attempts(self):
        from notifications import _resend_sender
        from notifications._resend_sender import ResendSender
        from resend.exceptions import RateLimitError

        transient = RateLimitError(
            code="429", error_type="rate_limit_exceeded", message="slow down"
        )
        with patch.object(_resend_sender.time, "sleep"):
            with patch("resend.Emails.send", side_effect=transient) as mock_send:
                result = ResendSender().send(
                    to="user@example.com", subject="hi", html="<p>x</p>", text="x"
                )
        assert result.success is False
        assert mock_send.call_count == _resend_sender._MAX_ATTEMPTS

    def test_send_uses_from_email_from_settings(self, settings):
        from notifications._resend_sender import ResendSender

        settings.RESEND_FROM_EMAIL = "noreply@example.com"
        settings.RESEND_API_KEY = "test_key"
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        # Inspect the params passed to resend.Emails.send
        args, kwargs = mock_send.call_args
        # The Resend SDK signature is resend.Emails.send(params) — params can be positional or keyword.
        # Find the params dict.
        params = args[0] if args else kwargs.get("params") or next(iter(kwargs.values()))
        assert params["from"] == "noreply@example.com"
        assert params["to"] == ["user@example.com"]
        assert params["subject"] == "hello"
        assert params["html"] == "<p>hi</p>"
        assert params["text"] == "hi"


class TestGetEmailSender:
    def test_returns_resend_sender_when_key_set(self, settings):
        from notifications._resend_sender import ResendSender
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = "test_key"
        settings.RESEND_FROM_EMAIL = "noreply@example.com"
        try:
            sender = get_email_sender()
            assert isinstance(sender, ResendSender)
        finally:
            reset_email_sender_cache()

    def test_returns_console_sender_when_no_key_in_dev(self, settings):
        from notifications._console_sender import ConsoleSender
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = ""
        try:
            sender = get_email_sender()
            assert isinstance(sender, ConsoleSender)
        finally:
            reset_email_sender_cache()

    def test_caches_sender_across_calls(self, settings):
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = ""
        try:
            first = get_email_sender()
            second = get_email_sender()
            assert first is second
        finally:
            reset_email_sender_cache()

    def test_raises_in_production_with_no_key(self, monkeypatch):
        from django.conf import settings
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        monkeypatch.setattr(settings, "RESEND_API_KEY", "")
        monkeypatch.setattr(settings, "IS_PRODUCTION", True)
        try:
            with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
                get_email_sender()
        finally:
            reset_email_sender_cache()
