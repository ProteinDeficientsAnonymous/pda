"""Tests for the magic-login email helper."""

import re
from unittest.mock import MagicMock

import pytest

from notifications._email_helpers import send_magic_login_email
from notifications.email_sender import SendResult


@pytest.mark.django_db
class TestSendMagicLoginEmail:
    def test_renders_and_sends_with_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            magic_link_url="https://pda.test/magic/abc",
        )

        assert result.success is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "user@example.com"
        assert "sam" in call_kwargs["text"].lower()
        assert "https://pda.test/magic/abc" in call_kwargs["text"]
        assert "https://pda.test/magic/abc" in call_kwargs["html"]

    def test_does_not_include_phone_number(self):
        """PII guard — the email body must not echo a phone number."""
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            magic_link_url="https://pda.test/magic/abc",
        )
        call_kwargs = sender.send.call_args.kwargs
        # No phone-number-shaped substring (+1 followed by 10 digits).
        assert re.search(r"\+1\d{10}", call_kwargs["text"]) is None
        assert re.search(r"\+1\d{10}", call_kwargs["html"]) is None

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="",
            magic_link_url="https://pda.test/magic/abc",
        )
        sender.send.assert_called_once()

    def test_subject_is_lowercase_friendly(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            magic_link_url="https://pda.test/magic/abc",
        )
        subject = sender.send.call_args.kwargs["subject"]
        # All lowercase per project ui-copy-tone rule
        assert subject == subject.lower()
        # Mentions login / pda
        assert "login" in subject or "log in" in subject
