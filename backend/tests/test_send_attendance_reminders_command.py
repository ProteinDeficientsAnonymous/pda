"""Tests for the send_attendance_reminders management command."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from community.models import AttendanceReminder, FeatureFlag, FeatureFlagState
from django.core.management import call_command
from django.test import override_settings
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import User

_PAST_JOINED = datetime(2020, 1, 1, tzinfo=UTC)


def _make_member(phone_number: str, **extra) -> User:
    user = User.objects.create_user(
        phone_number=phone_number,
        password="testpass123",
        first_name="Test",
        email=extra.pop("email", f"{phone_number}@example.test"),
        is_member=True,
        **extra,
    )
    User.objects.filter(pk=user.pk).update(date_joined=extra.get("date_joined", _PAST_JOINED))
    user.refresh_from_db()
    return user


@pytest.fixture
def fake_sender(monkeypatch):
    fake = MagicMock()
    fake.send.return_value = SendResult(success=True, provider_message_id="test_msg")
    monkeypatch.setattr(email_sender_module, "_cached_sender", fake)
    return fake


@pytest.fixture(autouse=True)
def _enable_flag(db):
    FeatureFlagState.objects.create(key=FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS, enabled=True)


@pytest.mark.django_db
class TestSendAttendanceRemindersCommand:
    def test_noop_when_flag_off(self, fake_sender):
        FeatureFlagState.objects.filter(key=FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS).update(
            enabled=False
        )
        _make_member("+12025550111")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()
        assert AttendanceReminder.objects.count() == 0

    def test_sends_and_records_reminder_for_due_member(self, fake_sender):
        user = _make_member("+12025550112")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_called_once()
        assert AttendanceReminder.objects.filter(user=user, milestone="m12").exists()

    def test_idempotent_second_run_sends_nothing(self, fake_sender):
        _make_member("+12025550113")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
            fake_sender.send.reset_mock()
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()
        assert AttendanceReminder.objects.count() == 1

    def test_excludes_paused_member(self, fake_sender):
        _make_member("+12025550114", is_paused=True)
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_archived_member(self, fake_sender):
        _make_member("+12025550115", archived_at=datetime.now(tz=UTC))
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_non_member(self, fake_sender):
        User.objects.create_user(
            phone_number="+12025550116",
            password="testpass123",
            email="guest@example.test",
            is_member=False,
        )
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_member_with_no_email(self, fake_sender):
        _make_member("+12025550117", email="")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()

    def test_skips_member_not_yet_due(self, fake_sender):
        _make_member("+12025550118")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=datetime.now(tz=UTC).date()):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_not_called()
        assert AttendanceReminder.objects.count() == 0

    def test_sends_only_latest_milestone_when_multiple_crossed(self, fake_sender):
        """A member whose clock jumped past 10mo and 11mo (e.g. cron was down)
        gets exactly one email — the 11mo one — not two."""
        from datetime import timedelta

        user = _make_member("+12025550119")
        floor = (datetime.now(tz=UTC) - timedelta(days=335)).date()
        with override_settings(ATTENDANCE_CLOCK_FLOOR=floor):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_called_once()
        reminders = AttendanceReminder.objects.filter(user=user)
        assert reminders.count() == 1
        assert reminders.first().milestone == "m11"
