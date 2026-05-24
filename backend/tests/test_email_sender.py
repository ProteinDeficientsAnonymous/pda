"""Tests for the email sender protocol and SendResult dataclass."""

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
