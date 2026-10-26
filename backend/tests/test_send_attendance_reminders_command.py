"""Tests for the send_attendance_reminders management command."""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from community.models import AttendanceReminder, AttendanceStatus, Event, EventRSVP, EventType
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
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
    monkeypatch.setattr(
        email_sender_module,
        "_cached_senders",
        dict.fromkeys(email_sender_module.EmailStream, fake),
    )
    return fake


@pytest.mark.django_db
class TestSendAttendanceRemindersCommand:
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

    def test_failed_send_does_not_record_reminder(self, fake_sender):
        user = _make_member("+12025550120")
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
        assert not AttendanceReminder.objects.filter(user=user).exists()

    def test_failed_send_retried_on_next_run(self, fake_sender):
        user = _make_member("+12025550121")
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders")
            fake_sender.send.return_value = SendResult(success=True, provider_message_id="msg")
            call_command("send_attendance_reminders")
        assert AttendanceReminder.objects.filter(user=user, milestone="m12").exists()

    def test_counts_failed_sends_separately(self, fake_sender):
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        out = StringIO()
        _make_member("+12025550122")
        with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
            call_command("send_attendance_reminders", stdout=out)
        assert "Sent 0 reminder(s); 1 failed." in out.getvalue()

    def test_sends_only_latest_milestone_when_multiple_crossed(self, fake_sender):
        """A member whose clock jumped past 10mo and 11mo (e.g. cron was down)
        gets exactly one email — the 11mo one — not two."""

        user = _make_member("+12025550119")
        floor = (datetime.now(tz=UTC) - timedelta(days=335)).date()
        with override_settings(ATTENDANCE_CLOCK_FLOOR=floor):
            call_command("send_attendance_reminders")
        fake_sender.send.assert_called_once()
        reminders = AttendanceReminder.objects.filter(user=user)
        assert reminders.count() == 1
        assert reminders.first().milestone == "m11"


@pytest.mark.django_db
def test_anchors_on_last_qualifying_attendance(fake_sender):
    user = _make_member("+12025550123")
    attended_at = datetime.now(tz=UTC) - timedelta(days=320)
    event = Event.objects.create(
        title="official", event_type=EventType.OFFICIAL, start_datetime=attended_at
    )
    EventRSVP.objects.create(
        user=user, event=event, status="attending", attendance=AttendanceStatus.ATTENDED
    )
    with override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()):
        call_command("send_attendance_reminders")
    fake_sender.send.assert_called_once()
    reminder = AttendanceReminder.objects.get(user=user)
    assert reminder.milestone == "m10"
    assert reminder.anchor_date == attended_at.date()


def _run_counting_queries(new_members: int, start: int) -> int:
    for i in range(start, start + new_members):
        user = _make_member(f"+1202555{i:04d}")
        AttendanceReminder.objects.create(
            user=user, milestone="m12", anchor_date=_PAST_JOINED.date()
        )
    with (
        override_settings(ATTENDANCE_CLOCK_FLOOR=_PAST_JOINED.date()),
        CaptureQueriesContext(connection) as ctx,
    ):
        call_command("send_attendance_reminders")
    return len(ctx.captured_queries)


@pytest.mark.django_db
def test_query_count_is_constant_in_member_count(fake_sender):
    small = _run_counting_queries(2, 1000)
    large = _run_counting_queries(6, 2000)
    assert large == small
    fake_sender.send.assert_not_called()
