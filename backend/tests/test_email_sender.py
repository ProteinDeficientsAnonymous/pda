"""Tests for the email sender protocol and SendResult dataclass."""

from unittest.mock import patch

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
