"""Tests for the join-approval email helper."""

from unittest.mock import MagicMock

import pytest
from notifications._email_helpers import send_join_approval_email
from notifications.email_sender import SendResult


@pytest.mark.django_db
class TestSendJoinApprovalEmail:
    def test_renders_and_sends_with_the_login_url(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            message_body="you now have full member access.",
            login_url="https://pda.test/login",
        )

        assert result.success is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "user@example.com"
        assert "https://pda.test/login" in call_kwargs["text"]
        assert "https://pda.test/login" in call_kwargs["html"]

    def test_carries_no_expiry_copy(self):
        """The login page never expires, so the old 7-day warning must be gone."""
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            message_body="you now have full member access.",
            login_url="https://pda.test/login",
        )
        call_kwargs = sender.send.call_args.kwargs
        assert "expires" not in call_kwargs["text"]
        assert "expires" not in call_kwargs["html"]

    def test_body_links_are_styled_anchors(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            message_body="join us: https://chat.whatsapp.com/abc123",
            login_url="https://pda.test/login",
        )
        html = sender.send.call_args.kwargs["html"]
        assert 'href="https://chat.whatsapp.com/abc123"' in html
        assert 'style="color: #3c6939;"' in html

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="",
            message_body="you now have full member access.",
            login_url="https://pda.test/login",
        )
        sender.send.assert_called_once()
