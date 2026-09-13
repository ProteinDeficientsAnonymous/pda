"""Tests for the whatsapp-join-reminder due-date calculation."""

from datetime import date, timedelta

from community._whatsapp_join_reminder import (
    GRACE_DAYS,
    INTERVAL_DAYS,
    MAX_REMINDERS,
    due_reminder_number,
)

_JOINED = date(2026, 1, 1)


def _due(**overrides):
    kwargs = {
        "joined_on": _JOINED,
        "sent_count": 0,
        "last_sent_on": None,
        "today": _JOINED,
    }
    kwargs.update(overrides)
    return due_reminder_number(**kwargs)


class TestFirstReminder:
    def test_not_due_on_join_day(self):
        assert _due(today=_JOINED) is None

    def test_not_due_inside_grace_period(self):
        assert _due(today=_JOINED + timedelta(days=GRACE_DAYS - 1)) is None

    def test_due_when_grace_period_elapsed(self):
        assert _due(today=_JOINED + timedelta(days=GRACE_DAYS)) == 1

    def test_due_long_after_grace_period(self):
        assert _due(today=_JOINED + timedelta(days=365)) == 1


class TestFollowUpReminders:
    def test_not_due_before_interval_elapses(self):
        sent_on = _JOINED + timedelta(days=GRACE_DAYS)
        assert (
            _due(
                sent_count=1,
                last_sent_on=sent_on,
                today=sent_on + timedelta(days=INTERVAL_DAYS - 1),
            )
            is None
        )

    def test_due_when_interval_elapses(self):
        sent_on = _JOINED + timedelta(days=GRACE_DAYS)
        assert (
            _due(
                sent_count=1,
                last_sent_on=sent_on,
                today=sent_on + timedelta(days=INTERVAL_DAYS),
            )
            == 2
        )

    def test_interval_measured_from_last_send_not_join_date(self):
        """A late first send pushes the second send out too — no catch-up burst."""
        late = _JOINED + timedelta(days=200)
        assert _due(sent_count=1, last_sent_on=late, today=late + timedelta(days=1)) is None

    def test_numbers_increment_with_sent_count(self):
        sent_on = _JOINED + timedelta(days=100)
        assert (
            _due(
                sent_count=MAX_REMINDERS - 1,
                last_sent_on=sent_on,
                today=sent_on + timedelta(days=INTERVAL_DAYS),
            )
            == MAX_REMINDERS
        )


class TestCap:
    def test_stops_after_max_reminders(self):
        sent_on = _JOINED + timedelta(days=100)
        assert (
            _due(
                sent_count=MAX_REMINDERS,
                last_sent_on=sent_on,
                today=sent_on + timedelta(days=INTERVAL_DAYS * 10),
            )
            is None
        )

    def test_stops_past_max_reminders(self):
        sent_on = _JOINED + timedelta(days=100)
        assert (
            _due(
                sent_count=MAX_REMINDERS + 5,
                last_sent_on=sent_on,
                today=sent_on + timedelta(days=INTERVAL_DAYS * 10),
            )
            is None
        )
