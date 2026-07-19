"""Tests for the event-invite email helper."""

from unittest.mock import MagicMock

import pytest
from notifications._email_helpers import EventInviteEmailDetails, send_event_invite_email
from notifications.email_sender import SendResult


def _details(**overrides) -> EventInviteEmailDetails:
    defaults = dict(
        to="user@example.com",
        display_name="Sam",
        inviter_name="Alice",
        event_title="Potluck",
        event_when="Saturday, June 14 at 6:00 PM",
        event_url="https://pda.test/events/abc",
    )
    defaults.update(overrides)
    return EventInviteEmailDetails(**defaults)


@pytest.mark.django_db
class TestSendEventInviteEmail:
    def test_renders_and_sends(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_event_invite_email(sender=sender, details=_details())

        assert result.success is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "user@example.com"
        assert "sam" in call_kwargs["text"].lower()
        assert "alice" in call_kwargs["text"].lower()
        assert "potluck" in call_kwargs["text"].lower()
        assert "https://pda.test/events/abc" in call_kwargs["text"]
        assert "https://pda.test/events/abc" in call_kwargs["html"]

    def test_handles_blank_display_name_and_when(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_event_invite_email(sender=sender, details=_details(display_name="", event_when=""))
        sender.send.assert_called_once()

    def test_subject_is_lowercase(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_event_invite_email(sender=sender, details=_details())
        subject = sender.send.call_args.kwargs["subject"]
        assert subject == subject.lower()
        assert "potluck" in subject
