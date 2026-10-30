import pytest
from community._cohost_reminder import due_cohost_reminder_events, send_due_cohost_reminders
from community.models import EventStatus, EventType
from django.core.management import call_command
from django.utils import timezone

from tests._digest_helpers import make_event, make_member


@pytest.fixture
def host(test_user):
    test_user.email = "host@example.com"
    test_user.save(update_fields=["email"])
    return test_user


def _make_event(host, days_out: float = 5, **extra):
    return make_event("Vegan Potluck", days_out, created_by=host, **extra)


def _due():
    return list(due_cohost_reminder_events(timezone.now()))


@pytest.mark.django_db
class TestDueCohostReminderEvents:
    def test_includes_official_event_with_only_creator(self, host):
        event = _make_event(host)
        assert _due() == [event]

    def test_excludes_event_with_cohost(self, host):
        event = _make_event(host)
        event.co_hosts.add(make_member("+12025556001"))
        assert _due() == []

    @pytest.mark.parametrize(
        "overrides",
        [
            {"event_type": EventType.COMMUNITY},
            {"event_type": EventType.CLUB},
            {"status": EventStatus.DRAFT},
            {"status": EventStatus.CANCELLED},
            {"days_out": 8},
            {"days_out": -0.05},
            {"cohost_reminder_sent_at": timezone.now()},
        ],
    )
    def test_excludes_ineligible(self, host, overrides):
        _make_event(host, **overrides)
        assert _due() == []

    def test_excludes_tbd_start(self, host):
        event = _make_event(host)
        event.start_datetime = None
        event.save(update_fields=["start_datetime"])
        assert _due() == []


@pytest.mark.django_db
class TestSendDueCohostReminders:
    def test_emails_host_and_stamps_once(self, host, fake_email_sender):
        event = _make_event(host)

        assert send_due_cohost_reminders() == 1
        assert send_due_cohost_reminders() == 0

        fake_email_sender.send.assert_called_once()
        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "host@example.com"
        assert "vegan potluck" in kwargs["subject"]
        assert f"/events/{event.pk}/edit" in kwargs["text"]
        assert "facilitators" in kwargs["text"]
        event.refresh_from_db()
        assert event.cohost_reminder_sent_at is not None

    def test_skips_host_without_email(self, test_user, fake_email_sender):
        event = _make_event(test_user)
        test_user.email = ""
        test_user.save(update_fields=["email"])

        assert send_due_cohost_reminders() == 1
        fake_email_sender.send.assert_not_called()
        event.refresh_from_db()
        assert event.cohost_reminder_sent_at is not None


@pytest.mark.django_db
def test_command_reports_count(host, fake_email_sender, capsys):
    _make_event(host)
    call_command("send_cohost_reminders")
    assert "Sent 1 co-host reminder(s)" in capsys.readouterr().out
