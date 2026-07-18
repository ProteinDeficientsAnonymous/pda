"""Tests for the join-approval email helper."""

from unittest.mock import MagicMock

import pytest
from notifications._email_helpers import send_join_approval_email
from notifications.email_sender import SendResult


@pytest.mark.django_db
class TestSendJoinApprovalEmail:
    def test_renders_and_sends_with_magic_link(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            message_body="you now have full member access.",
            magic_link_url="https://pda.test/magic-login/abc",
        )

        assert result.success is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "user@example.com"
        assert "https://pda.test/magic-login/abc" in call_kwargs["text"]
        assert "https://pda.test/magic-login/abc" in call_kwargs["html"]

    def test_mentions_link_expiry(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            message_body="you now have full member access.",
            magic_link_url="https://pda.test/magic-login/abc",
        )
        call_kwargs = sender.send.call_args.kwargs
        assert "7 days" in call_kwargs["text"]
        assert "7 days" in call_kwargs["html"]

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_join_approval_email(
            sender=sender,
            to="user@example.com",
            display_name="",
            message_body="you now have full member access.",
            magic_link_url="https://pda.test/magic-login/abc",
        )
        sender.send.assert_called_once()
