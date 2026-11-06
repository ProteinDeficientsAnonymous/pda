from unittest.mock import MagicMock

import pytest
from community.models import RSVPStatus
from notifications.email_sender import SendResult
from notifications.rsvp_reminder_email import RsvpReminderEmailDetails, send_rsvp_reminder_email


@pytest.mark.parametrize(
    "status, line",
    [
        (RSVPStatus.ATTENDING, "you're going"),
        (RSVPStatus.MAYBE, "you rsvp'd maybe"),
        (RSVPStatus.WAITLISTED, "you're on the waitlist"),
    ],
)
def test_renders_status_line_and_link(status, line):
    sender = MagicMock()
    sender.send.return_value = SendResult(success=True)
    details = RsvpReminderEmailDetails(
        to="guest@example.com",
        display_name="Sam",
        status=status,
        event_title="Vegan Potluck",
        event_when="Saturday, November 7 at 12:00 PM",
        event_location="The Park",
        rsvp_url="https://pda.test/events/vegan-potluck",
    )

    send_rsvp_reminder_email(sender=sender, details=details)

    kwargs = sender.send.call_args.kwargs
    assert kwargs["to"] == "guest@example.com"
    assert kwargs["subject"] == "reminder: vegan potluck is tomorrow"
    for body in (kwargs["text"], kwargs["html"]):
        assert line in body
        assert "the park" in body
        assert "https://pda.test/events/vegan-potluck" in body
