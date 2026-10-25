from unittest.mock import MagicMock

from notifications._digest_emails import send_monthly_digest_email
from notifications.email_sender import SendResult


class TestSendMonthlyDigestEmail:
    def test_renders_month_and_events(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="msg")
        send_monthly_digest_email(
            sender=sender,
            to="ada@example.test",
            display_name="Ada",
            month="June",
            events=[{"title": "Potluck", "when": "Friday", "url": "https://pda.test/events/p"}],
            urls={
                "calendar_url": "https://pda.test/calendar",
                "settings_url": "https://pda.test/s",
            },
        )
        kwargs = sender.send.call_args.kwargs
        assert kwargs["subject"] == "what's coming up in june at pda"
        assert "hi ada" in kwargs["text"]
        assert "here's what's coming up in june:" in kwargs["text"]
        assert "potluck" in kwargs["text"]
        assert 'href="https://pda.test/events/p"' in kwargs["html"]
