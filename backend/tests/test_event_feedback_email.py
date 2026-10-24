from unittest.mock import MagicMock

import pytest
from notifications._event_feedback_email import send_event_feedback_email
from notifications.email_sender import SendResult

URL = "https://pda.test/feedback#abc123"


def _send(*, reminder: bool, event_date: str | None = "oct 12", display_name: str = "Sam"):
    sender = MagicMock()
    sender.send.return_value = SendResult(success=True, provider_message_id="m1")
    result = send_event_feedback_email(
        sender=sender,
        to="member@example.test",
        display_name=display_name,
        event_title="Vegan Potluck",
        event_date=event_date,
        url=URL,
        reminder=reminder,
    )
    return result, sender.send.call_args.kwargs


@pytest.mark.django_db
class TestSendEventFeedbackEmail:
    def test_request_has_link_title_and_lowercase_subject(self):
        result, kwargs = _send(reminder=False)
        assert result.success is True
        assert kwargs["to"] == "member@example.test"
        assert kwargs["subject"] == "how was vegan potluck?"
        for body in (kwargs["html"], kwargs["text"]):
            assert URL in body
            assert "vegan potluck" in body
            assert "oct 12" in body

    def test_reminder_has_distinct_subject_and_copy(self):
        _, kwargs = _send(reminder=True)
        assert kwargs["subject"] == "still keen to hear about vegan potluck"
        assert "haven't filled it out yet" in kwargs["text"]
        assert URL in kwargs["html"]

    @pytest.mark.parametrize("reminder", [False, True])
    def test_handles_missing_date_and_name(self, reminder):
        _, kwargs = _send(reminder=reminder, event_date=None, display_name="")
        assert URL in kwargs["text"]
        assert "none" not in kwargs["text"].lower()

    @pytest.mark.parametrize("reminder", [False, True])
    def test_text_copy_is_lowercase(self, reminder):
        _, kwargs = _send(reminder=reminder)
        letters = "".join(ch for ch in kwargs["text"].replace(URL, "") if ch.isalpha())
        assert letters == letters.lower()
