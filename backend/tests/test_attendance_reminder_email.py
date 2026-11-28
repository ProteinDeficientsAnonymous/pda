"""Tests for the attendance-reminder email helper."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from community.models import AttendanceMilestone
from notifications.attendance_reminder_email import send_attendance_reminder_email
from notifications.email_sender import SendResult

DEADLINE = date(2027, 3, 1)


@pytest.fixture(autouse=True)
def _base_url(settings):
    settings.FRONTEND_BASE_URL = "https://pda.test"


@pytest.mark.django_db
class TestSendAttendanceReminderEmail:
    @pytest.mark.parametrize(
        "milestone",
        [
            AttendanceMilestone.M10,
            AttendanceMilestone.M11,
            AttendanceMilestone.M11_5,
            AttendanceMilestone.M12,
        ],
    )
    def test_renders_and_sends_each_milestone(self, milestone):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_attendance_reminder_email(
            sender=sender,
            to="member@example.test",
            display_name="Sam",
            milestone=milestone,
            deadline=DEADLINE,
        )

        assert result.success is True
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "member@example.test"
        assert "https://pda.test/calendar" in call_kwargs["html"]
        assert "https://pda.test/calendar" in call_kwargs["text"]
        assert call_kwargs["subject"] == call_kwargs["subject"].lower()
        assert "march 1, 2027" in call_kwargs["text"]
        assert "march 1, 2027" in call_kwargs["html"]

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_attendance_reminder_email(
            sender=sender,
            to="member@example.test",
            display_name="",
            milestone=AttendanceMilestone.M10,
            deadline=DEADLINE,
        )
        sender.send.assert_called_once()

    def test_body_copy_is_lowercase(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_attendance_reminder_email(
            sender=sender,
            to="member@example.test",
            display_name="Sam",
            milestone=AttendanceMilestone.M12,
            deadline=DEADLINE,
        )
        text = sender.send.call_args.kwargs["text"]
        letters_only = "".join(ch for ch in text if ch.isalpha())
        assert letters_only == letters_only.lower()
