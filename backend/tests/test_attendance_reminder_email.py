"""Tests for the attendance-reminder email helper."""

from unittest.mock import MagicMock

import pytest
from community.models import AttendanceMilestone
from notifications._attendance_reminder_email import send_attendance_reminder_email
from notifications.email_sender import SendResult


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
            calendar_url="https://pda.test/calendar",
            milestone=milestone,
        )

        assert result.success is True
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "member@example.test"
        assert "https://pda.test/calendar" in call_kwargs["html"]
        assert "https://pda.test/calendar" in call_kwargs["text"]
        assert call_kwargs["subject"] == call_kwargs["subject"].lower()

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_attendance_reminder_email(
            sender=sender,
            to="member@example.test",
            display_name="",
            calendar_url="https://pda.test/calendar",
            milestone=AttendanceMilestone.M10,
        )
        sender.send.assert_called_once()

    def test_body_copy_is_lowercase(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_attendance_reminder_email(
            sender=sender,
            to="member@example.test",
            display_name="Sam",
            calendar_url="https://pda.test/calendar",
            milestone=AttendanceMilestone.M12,
        )
        text = sender.send.call_args.kwargs["text"]
        letters_only = "".join(ch for ch in text if ch.isalpha())
        assert letters_only == letters_only.lower()
