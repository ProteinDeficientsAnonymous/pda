from datetime import UTC, datetime, timedelta

import pytest
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from community.scheduled.rsvp_deadline_reminder import (
    due_deadline_reminders,
    send_due_deadline_reminders,
)
from django.core.management import call_command
from django.utils import timezone

from tests._public_rsvp_helpers import make_public_rsvper
from tests._users import make_user

H = timedelta(hours=1)
SENT_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _maybe(deadline_in=12 * H, *, user=None, event_kwargs=None, **rsvp_kwargs) -> EventRSVP:
    event = Event.objects.create(
        **{
            "title": "Potluck",
            "start_datetime": timezone.now() + timedelta(days=3),
            "rsvp_enabled": True,
            "rsvp_deadline": None if deadline_in is None else timezone.now() + deadline_in,
            **(event_kwargs or {}),
        }
    )
    rsvp_kwargs.setdefault("status", RSVPStatus.MAYBE)
    return EventRSVP.objects.create(event=event, user=user or make_user(), **rsvp_kwargs)


def _due() -> list[EventRSVP]:
    return list(due_deadline_reminders(timezone.now()))


@pytest.mark.django_db
class TestDueDeadlineReminders:
    def test_includes_maybe_within_a_day(self):
        rsvp = _maybe()
        assert _due() == [rsvp]

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"status": RSVPStatus.ATTENDING}, id="going"),
            pytest.param({"status": RSVPStatus.CANT_GO}, id="cant-go"),
            pytest.param({"status": RSVPStatus.WAITLISTED}, id="waitlisted"),
            pytest.param({"deadline_in": None}, id="no-deadline"),
            pytest.param({"deadline_in": 25 * H}, id="deadline-too-far"),
            pytest.param({"deadline_in": -H}, id="deadline-passed"),
            pytest.param({"event_kwargs": {"status": EventStatus.CANCELLED}}, id="cancelled"),
            pytest.param({"event_kwargs": {"rsvp_enabled": False}}, id="rsvps-off"),
            pytest.param({"rsvp_deadline_reminder_sent_at": SENT_AT}, id="already-sent"),
        ],
    )
    def test_excludes_ineligible(self, kwargs):
        _maybe(**kwargs)
        assert _due() == []

    def test_excludes_users_without_email(self):
        _maybe(user=make_user(email=""))
        assert _due() == []


@pytest.mark.django_db
class TestSendDeadlineReminders:
    def test_sends_once_per_rsvp(self, fake_email_sender):
        rsvp = _maybe(user=make_user(email="maybe@example.com"))

        assert send_due_deadline_reminders(fake_email_sender) == 1
        assert send_due_deadline_reminders(fake_email_sender) == 0

        fake_email_sender.send.assert_called_once()
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "maybe@example.com"
        assert kwargs["subject"] == "confirm your rsvp to potluck"
        assert f"/events/{rsvp.event.slug}" in kwargs["text"]
        rsvp.refresh_from_db()
        assert rsvp.rsvp_deadline_reminder_sent_at is not None

    def test_public_rsvper_gets_manage_link(self, fake_email_sender):
        _maybe(user=make_public_rsvper("+14155550451", "pub@example.com"))
        send_due_deadline_reminders(fake_email_sender)
        assert "/my-rsvps?token=" in fake_email_sender.send.call_args.kwargs["text"]

    def test_failed_send_still_claims(self, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("boom")
        rsvp = _maybe()
        assert send_due_deadline_reminders(fake_email_sender) == 1
        rsvp.refresh_from_db()
        assert rsvp.rsvp_deadline_reminder_sent_at is not None

    def test_command(self, fake_email_sender, capsys):
        _maybe()
        call_command("send_rsvp_deadline_reminders")
        assert "Sent 1 rsvp deadline reminder(s)" in capsys.readouterr().out
