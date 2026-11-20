from unittest.mock import MagicMock

from notifications.email_sender import SendResult
from notifications.rsvp_deadline_email import (
    RsvpDeadlineReminderEmailDetails,
    send_rsvp_deadline_reminder_email,
)


def test_renders_deadline_and_link():
    sender = MagicMock()
    sender.send.return_value = SendResult(success=True)
    details = RsvpDeadlineReminderEmailDetails(
        to="maybe@example.com",
        display_name="Sam",
        event_title="Sam's Potluck & Games",
        deadline="Friday, March 6 at 6:00 PM",
        rsvp_url="https://pda.test/my-rsvps?token=a&b=1",
    )

    send_rsvp_deadline_reminder_email(sender=sender, details=details)

    kwargs = sender.send.call_args.kwargs
    assert kwargs["to"] == "maybe@example.com"
    assert kwargs["subject"] == "confirm your rsvp to sam's potluck & games"
    for body in (kwargs["text"], kwargs["html"]):
        assert "hi sam" in body
        assert "friday, march 6 at 6:00 pm" in body
    assert "sam's potluck & games" in kwargs["text"]
    assert "https://pda.test/my-rsvps?token=a&b=1" in kwargs["text"]
