from datetime import datetime

import pytest
from community.models import EventStatus, EventType, RSVPStatus
from community.rsvps.reminder import due_rsvp_reminder_events, send_due_rsvp_reminders
from django.core.management import call_command

from tests._digest_helpers import make_tentative
from tests._event_feedback_helpers import NOW, TZ
from tests._events import make_event, make_rsvp
from tests._users import make_user

TOMORROW_NOON = datetime(2026, 10, 16, 12, 0, tzinfo=TZ)


def _event(**extra):
    extra.setdefault("start_datetime", TOMORROW_NOON)
    return make_event(title="Vegan Potluck", location="the park", **extra)


@pytest.mark.django_db
class TestDueRsvpReminderEvents:
    @pytest.mark.parametrize("hour", [0, 23])
    def test_includes_events_starting_tomorrow(self, hour):
        event = _event(start_datetime=TOMORROW_NOON.replace(hour=hour))
        assert list(due_rsvp_reminder_events(NOW)) == [event]

    @pytest.mark.parametrize(
        "overrides",
        [
            {"start_datetime": datetime(2026, 10, 15, 23, 0, tzinfo=TZ)},
            {"start_datetime": datetime(2026, 10, 17, 0, 0, tzinfo=TZ)},
            {"status": EventStatus.CANCELLED},
            {"status": EventStatus.DRAFT},
            {"datetime_tbd": True},
            {"rsvp_reminder_sent_at": NOW},
        ],
    )
    def test_excludes_ineligible(self, overrides):
        _event(**overrides)
        assert list(due_rsvp_reminder_events(NOW)) == []


@pytest.mark.django_db
class TestSendDueRsvpReminders:
    def test_emails_reminded_statuses_once(self, fake_email_sender):
        event = _event()
        for status in RSVPStatus:
            make_rsvp(event, make_user(), status)
        make_rsvp(event, make_user(email=""))

        assert send_due_rsvp_reminders(NOW) == 3
        assert send_due_rsvp_reminders(NOW) == 0
        assert fake_email_sender.send.call_count == 3
        event.refresh_from_db()
        assert event.rsvp_reminder_sent_at == NOW

    @pytest.mark.parametrize(
        "make_guest, event_type, link",
        [
            (make_user, EventType.COMMUNITY, "/events/"),
            (lambda: make_tentative("+12025558001"), EventType.OFFICIAL, "/events/"),
            (lambda: make_tentative("+12025558002"), EventType.COMMUNITY, "/my-rsvps?token="),
            (lambda: make_user(is_member=False), EventType.OFFICIAL, "/my-rsvps?token="),
        ],
    )
    def test_link_matches_guest_kind(self, fake_email_sender, make_guest, event_type, link):
        make_rsvp(_event(event_type=event_type), make_guest())
        send_due_rsvp_reminders(NOW)
        assert link in fake_email_sender.send.call_args.kwargs["text"]


@pytest.mark.django_db
def test_command_reports_count(fake_email_sender, capsys):
    call_command("send_rsvp_reminders")
    assert "Sent 0 rsvp reminder(s)" in capsys.readouterr().out
