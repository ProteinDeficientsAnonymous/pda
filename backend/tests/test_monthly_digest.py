from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from community.management.commands import send_monthly_digest as digest_command
from community.models import Event, EventType
from django.core.management import call_command
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications._digest_emails import send_monthly_digest_email
from notifications.email_sender import EmailStream, SendResult

from tests.test_weekly_digest import _make_event, _make_member, _make_tentative

# 12:00 UTC is 8am eastern, when the daily cron runs.
FIRST_OF_JUNE = datetime(2026, 6, 1, 12, 0, 0)


def _freeze(monkeypatch, when: datetime) -> None:
    frozen = timezone.make_aware(when)
    monkeypatch.setattr(digest_command.timezone, "now", lambda: frozen)


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
class TestSendMonthlyDigestCommand:
    def test_skips_when_not_the_first(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, datetime(2026, 6, 2, 12, 0, 0))
        _make_member("+12025550301")
        _make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_sends_this_months_events_on_the_first(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        _make_member("+12025550302")
        _make_event("potluck", 3)
        _make_event("film night", 20)
        _make_event("july picnic", 31)
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()
        kwargs = fake_sender.send.call_args.kwargs
        assert kwargs["subject"] == "what's coming up in june at pda"
        assert "here's what's coming up in june:" in kwargs["text"]
        assert "potluck" in kwargs["text"]
        assert "film night" in kwargs["text"]
        assert "july picnic" not in kwargs["text"]

    def test_month_ends_at_eastern_midnight(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        _make_member("+12025550303")
        july_first_eastern = timezone.make_aware(datetime(2026, 7, 1, 4, 0, 0))
        for title, start in (
            ("late june show", july_first_eastern - timedelta(minutes=1)),
            ("july 1 brunch", july_first_eastern),
        ):
            Event.objects.create(
                title=title,
                start_datetime=start,
                location="the park",
                event_type=EventType.OFFICIAL,
            )
        call_command("send_monthly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "late june show" in text
        assert "july 1 brunch" not in text

    def test_skips_member_opted_out(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        _make_member("+12025550309", weekly_digest_opt_out=True)
        _make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_uses_bulk_email_stream(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        _make_member("+12025550310")
        _make_event("potluck", 3)
        call_command("send_monthly_digest")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_to_sends_regardless_of_date(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, datetime(2026, 6, 15, 12, 0, 0))
        _make_member("+12025550311")
        _make_event("potluck", 3)
        call_command("send_monthly_digest", to="probe@example.com")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == "probe@example.com"


@pytest.mark.django_db
class TestMonthlyDigestTentativeMembers:
    def test_sends_to_tentative_member(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        tentative = _make_tentative("+12025550321")
        _make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == tentative.email


class TestSendMonthlyDigestEmail:
    def test_renders_month_and_events(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="msg")
        send_monthly_digest_email(
            sender=sender,
            to="ada@example.test",
            display_name="Ada",
            month="June",
            events=[{"title": "Potluck", "when": "Friday", "url": "https://pda.test/events/p"}],
            urls={
                "calendar_url": "https://pda.test/calendar",
                "settings_url": "https://pda.test/s",
            },
        )
        kwargs = sender.send.call_args.kwargs
        assert kwargs["subject"] == "what's coming up in june at pda"
        assert "hi ada" in kwargs["text"]
        assert "here's what's coming up in june:" in kwargs["text"]
        assert "potluck" in kwargs["text"]
        assert 'href="https://pda.test/events/p"' in kwargs["html"]
