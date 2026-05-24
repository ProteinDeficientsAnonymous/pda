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
