from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from community.management.commands import send_monthly_digest as digest_command
from community.models import Event, EventType
from django.core.management import call_command
from django.utils import timezone
from notifications._digest_emails import send_monthly_digest_email
from notifications.email_sender import EmailStream, SendResult

from tests._digest_helpers import make_event, make_member, make_tentative

# The monthly cron runs at 12:00 UTC: early morning of the same day in eastern, any time of year.
FIRST_OF_JUNE = datetime(2026, 6, 1, 12, 0, 0)


def _freeze(monkeypatch, when: datetime) -> None:
    frozen = timezone.make_aware(when)
    monkeypatch.setattr(digest_command.timezone, "now", lambda: frozen)


def _shoutout(phone_number: str, first_name: str, year: int, month: int = 6, **extra):
    return make_member(
        phone_number,
        first_name=first_name,
        veganniversary_month=month,
        veganniversary_year=year,
        veganniversary_shoutout_opt_in=True,
        **extra,
    )


@pytest.mark.django_db
class TestSendMonthlyDigestCommand:
    def test_skips_when_not_the_first(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, datetime(2026, 6, 2, 12, 0, 0))
        make_member("+12025550301")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_sends_this_months_events_on_the_first(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550302")
        make_event("potluck", 3)
        make_event("film night", 20)
        make_event("july picnic", 31)
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
        make_member("+12025550303")
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

    def test_december_runs_through_new_years_eve(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, datetime(2026, 12, 1, 12, 0, 0))
        make_member("+12025550316")
        make_event("solstice potluck", 20)
        make_event("new year brunch", 32)
        call_command("send_monthly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "solstice potluck" in text
        assert "new year brunch" not in text

    def test_includes_veganniversaries_grouped_by_years(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        bo = _shoutout("+12025550305", "Bo", 2021)
        ada = _shoutout("+12025550304", "Ada", 2021)
        _shoutout("+12025550306", "Cam", 2025)
        call_command("send_monthly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        html = fake_sender.send.call_args.kwargs["html"]
        assert "happy june veganniversary!" in text
        assert "5 years" in text
        assert "1 year" in text
        assert "cam" in text
        assert text.index("5 years") < text.index("1 year")
        assert text.index("ada") < text.index("bo")
        assert f"http://localhost:3000/members/{ada.pk}" in text
        assert f'href="http://localhost:3000/members/{bo.pk}"' in html

    def test_omits_veganniversary_in_other_month(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        _shoutout("+12025550307", "Dana", 2018, month=7)
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "veganniversary" not in text

    def test_omits_without_shoutout_opt_in(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member(
            "+12025550308",
            first_name="Fay",
            veganniversary_month=6,
            veganniversary_year=2024,
            veganniversary_shoutout_opt_in=False,
        )
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_member_opted_out(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550309", monthly_digest_opt_out=True)
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_rerun_on_the_first_does_not_resend(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550313")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()

    def test_rerun_retries_failed_sends(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550314")
        make_event("potluck", 3)
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        call_command("send_monthly_digest")
        fake_sender.send.return_value = SendResult(success=True, provider_message_id="ok")
        call_command("send_monthly_digest")
        assert fake_sender.send.call_count == 2

    def test_sends_again_next_month(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550315")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        _freeze(monkeypatch, datetime(2026, 7, 1, 12, 0, 0))
        make_event("july potluck", 3)
        call_command("send_monthly_digest")
        assert fake_sender.send.call_count == 2

    def test_weekly_opt_out_still_gets_monthly(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_member("+12025550312", weekly_digest_opt_out=True)
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()

    def test_uses_bulk_email_stream(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        make_member("+12025550310")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_to_sends_regardless_of_date(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, datetime(2026, 6, 15, 12, 0, 0))
        make_member("+12025550311")
        make_event("potluck", 3)
        call_command("send_monthly_digest", to="probe@example.com")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == "probe@example.com"


@pytest.mark.django_db
class TestMonthlyDigestTentativeMembers:
    def test_sends_to_tentative_member(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        tentative = make_tentative("+12025550321")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == tentative.email

    def test_omits_veganniversaries_for_tentative_member(self, fake_sender, monkeypatch):
        """Shoutouts link to member profiles, which a tentative member can't open."""
        _freeze(monkeypatch, FIRST_OF_JUNE)
        member = _shoutout("+12025550320", "Ada", 2021)
        tentative = make_tentative("+12025550321")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        texts = {c.kwargs["to"]: c.kwargs["text"] for c in fake_sender.send.call_args_list}
        assert "veganniversary" in texts[member.email]
        assert "potluck" in texts[tentative.email]
        assert "veganniversary" not in texts[tentative.email]

    def test_skips_tentative_member_opted_out(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_tentative("+12025550324", monthly_digest_opt_out=True)
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        fake_sender.send.assert_not_called()

    def test_rerun_does_not_resend_to_tentative_member(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        make_tentative("+12025550325")
        make_event("potluck", 3)
        call_command("send_monthly_digest")
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()

    def test_skips_tentative_member_when_only_veganniversaries(self, fake_sender, monkeypatch):
        _freeze(monkeypatch, FIRST_OF_JUNE)
        member = _shoutout("+12025550322", "Gus", 2024)
        make_tentative("+12025550323")
        call_command("send_monthly_digest")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == member.email


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

    def test_renders_without_events(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="msg")
        send_monthly_digest_email(
            sender=sender,
            to="ada@example.test",
            display_name="Ada",
            month="June",
            events=[],
            urls={
                "calendar_url": "https://pda.test/calendar",
                "settings_url": "https://pda.test/s",
            },
            veganniversaries=[{"label": "1 year", "people": [{"name": "Bo", "url": "u"}]}],
        )
        text = sender.send.call_args.kwargs["text"]
        assert "coming up in june:" not in text
        assert "happy june veganniversary!" in text
        assert "see the full calendar" in text
