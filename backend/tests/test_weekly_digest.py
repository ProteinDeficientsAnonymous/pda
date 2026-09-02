"""Tests for the send_weekly_digest management command."""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from community.models import Event, EventStatus, EventType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import EmailStream, SendResult
from users.models import User


def _freeze_digest(monkeypatch, when: datetime) -> None:
    frozen = timezone.make_aware(when)
    monkeypatch.setattr(
        "community.management.commands.send_weekly_digest.timezone.now",
        lambda: frozen,
    )
    monkeypatch.setattr("django.utils.timezone.now", lambda: frozen)


def _make_member(phone_number: str, **extra) -> User:
    extra.setdefault("email", f"{phone_number}@example.test")
    extra.setdefault("first_name", "Test")
    extra.setdefault("is_member", True)
    return User.objects.create_user(
        phone_number=phone_number,
        password="testpass123",
        **extra,
    )


def _make_event(title: str, days_out: float, **extra) -> Event:
    extra.setdefault("event_type", EventType.OFFICIAL)
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=days_out),
        location="the park",
        **extra,
    )


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
class TestSendWeeklyDigestCommand:
    def test_no_events_in_range_sends_nothing(self, fake_sender):
        _make_member("+12025550202")
        _make_event("far off potluck", 30)
        _make_event("last week's potluck", -3)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_sends_to_each_member_with_email(self, fake_sender):
        _make_member("+12025550203")
        _make_member("+12025550204")
        _make_event("potluck", 2)
        _make_event("film night", 5)
        call_command("send_weekly_digest")
        assert fake_sender.send.call_count == 2

    def test_uses_bulk_email_stream(self, fake_sender, monkeypatch):
        """The digest fans out to every member — it must not spend transactional quota."""
        from community.management.commands import send_weekly_digest as digest_command

        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        _make_member("+12025550250")
        _make_event("park cleanup", 2)
        call_command("send_weekly_digest")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_to_sends_single_digest_to_that_address(self, fake_sender):
        _make_member("+12025550260")
        _make_member("+12025550261")
        _make_event("potluck", 2)
        call_command("send_weekly_digest", to="probe@example.com")
        assert fake_sender.send.call_count == 1
        assert fake_sender.send.call_args.kwargs["to"] == "probe@example.com"

    def test_to_uses_first_name_of_matching_user(self, fake_sender):
        _make_member("+12025550262", email="known@example.com")
        _make_event("potluck", 2)
        call_command("send_weekly_digest", to="known@example.com")
        assert "hi test" in fake_sender.send.call_args.kwargs["text"]

    def test_to_raises_when_send_fails(self, fake_sender):
        fake_sender.send.return_value = SendResult(
            success=False, error="http 401 code=unauthorized"
        )
        _make_event("potluck", 2)
        with pytest.raises(CommandError, match="unauthorized"):
            call_command("send_weekly_digest", to="probe@example.com")

    def test_to_still_uses_bulk_stream(self, fake_sender, monkeypatch):
        from community.management.commands import send_weekly_digest as digest_command

        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        _make_event("potluck", 2)
        call_command("send_weekly_digest", to="probe@example.com")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_digest_lists_both_events(self, fake_sender):
        _make_member("+12025550205")
        _make_event("potluck", 2)
        _make_event("film night", 5)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "potluck" in text
        assert "film night" in text

    def test_skips_member_with_no_email(self, fake_sender):
        _make_member("+12025550206", email="")
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_cancelled_and_deleted_events(self, fake_sender):
        _make_member("+12025550207")
        _make_event("cancelled potluck", 2, status=EventStatus.CANCELLED)
        _make_event("deleted potluck", 3, status=EventStatus.DELETED)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_soft_deleted_event(self, fake_sender):
        _make_member("+12025550208")
        _make_event("removed potluck", 2, deleted_at=timezone.now())
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_includes_official_and_club_events(self, fake_sender):
        _make_member("+12025550213")
        _make_event("official meetup", 2, event_type=EventType.OFFICIAL)
        _make_event("book club", 3, event_type=EventType.CLUB)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "official meetup" in text
        assert "book club" in text

    def test_excludes_community_events(self, fake_sender):
        _make_member("+12025550214")
        _make_event("random hangout", 2, event_type=EventType.COMMUNITY)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_non_member(self, fake_sender):
        User.objects.create_user(
            phone_number="+12025550209",
            password="testpass123",
            email="guest@example.test",
            is_member=False,
        )
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_member_opted_out(self, fake_sender):
        _make_member("+12025550210", weekly_digest_opt_out=True)
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_paused_member(self, fake_sender):
        _make_member("+12025550212", is_paused=True)
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_email_links_to_settings(self, fake_sender):
        _make_member("+12025550211")
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "/settings" in text

    def test_counts_failed_sends_separately(self, fake_sender):
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        _make_member("+12025550215")
        _make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 0 digest(s); 1 failed." in out.getvalue()

    def test_reports_zero_failures_on_success(self, fake_sender):
        _make_member("+12025550216")
        _make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 digest(s); 0 failed." in out.getvalue()

    def test_counts_mixed_success_and_failure(self, fake_sender):
        fake_sender.send.side_effect = [
            SendResult(success=True, provider_message_id="test_msg"),
            SendResult(success=False, error="boom"),
        ]
        _make_member("+12025550217")
        _make_member("+12025550218")
        _make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 digest(s); 1 failed." in out.getvalue()

    def test_formats_event_time_in_eastern_not_utc(self, fake_sender):
        _make_member("+12025550219")
        start = (
            (timezone.now() + timedelta(days=2))
            .astimezone(ZoneInfo("America/New_York"))
            .replace(hour=18, minute=0, second=0, microsecond=0)
        )
        Event.objects.create(
            title="potluck",
            start_datetime=start,
            location="the park",
            event_type=EventType.OFFICIAL,
        )
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "6:00 pm" in text
        utc_clock = start.astimezone(UTC).strftime("%I:%M %p").lstrip("0").lower()
        assert utc_clock not in text

    def test_includes_veganversaries_in_first_week_grouped_by_years(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 3, 12, 0, 0))
        _make_member("+12025550219")
        ada = _make_member(
            "+12025550220",
            first_name="Ada",
            veganversary_month=6,
            veganversary_day=20,
            veganversary_year=2021,
        )
        bo = _make_member(
            "+12025550221",
            first_name="Bo",
            veganversary_month=6,
            veganversary_day=1,
            veganversary_year=2021,
        )
        _make_member(
            "+12025550222",
            first_name="Cam",
            veganversary_month=6,
            veganversary_day=None,
            veganversary_year=2025,
        )
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        html = fake_sender.send.call_args.kwargs["html"]
        assert "if you see these people, tell them happy veganversary!" in text
        assert "5 years" in text
        assert "1 year" in text
        assert "ada" in text
        assert "bo" in text
        assert "cam" in text
        assert f"http://localhost:3000/members/{ada.pk}" in text
        assert f"http://localhost:3000/members/{bo.pk}" in text
        assert f'href="http://localhost:3000/members/{ada.pk}"' in html
        assert f'href="http://localhost:3000/members/{bo.pk}"' in html

    def test_omits_veganversary_in_other_month(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 3, 12, 0, 0))
        _make_member("+12025550223")
        _make_member(
            "+12025550224",
            first_name="Dana",
            veganversary_month=7,
            veganversary_day=15,
            veganversary_year=2018,
        )
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "happy veganversary" not in text

    def test_omits_veganversaries_after_first_week(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 7, 12, 0, 0))
        _make_member("+12025550225")
        _make_member(
            "+12025550226",
            first_name="Eve",
            veganversary_month=6,
            veganversary_day=8,
            veganversary_year=2023,
        )
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "happy veganversary" not in text

    def test_omits_shoutout_opt_out(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 3, 12, 0, 0))
        _make_member(
            "+12025550227",
            first_name="Fay",
            veganversary_month=6,
            veganversary_year=2024,
            veganversary_shoutout_opt_out=True,
        )
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_sends_digest_when_only_veganversaries_this_month(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 3, 12, 0, 0))
        _make_member(
            "+12025550228",
            first_name="Gus",
            veganversary_month=6,
            veganversary_day=20,
            veganversary_year=2024,
        )
        call_command("send_weekly_digest")
        fake_sender.send.assert_called_once()
        text = fake_sender.send.call_args.kwargs["text"]
        assert "gus" in text
        assert "2 years" in text
