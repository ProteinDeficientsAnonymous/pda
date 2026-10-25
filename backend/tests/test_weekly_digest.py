"""Tests for the send_weekly_digest management command."""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from community.management.commands import send_weekly_digest as digest_command
from community.models import Event, EventStatus, EventType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from notifications.email_sender import EmailStream, SendResult
from users.models import User

from tests._digest_helpers import make_event, make_member, make_tentative


def _freeze_digest(monkeypatch, when: datetime) -> None:
    frozen = timezone.make_aware(when)
    monkeypatch.setattr(
        "community.management.commands.send_weekly_digest.timezone.now",
        lambda: frozen,
    )
    monkeypatch.setattr("django.utils.timezone.now", lambda: frozen)


@pytest.mark.django_db
class TestSendWeeklyDigestCommand:
    def test_no_events_in_range_sends_nothing(self, fake_sender):
        make_member("+12025550202")
        make_event("far off potluck", 30)
        make_event("last week's potluck", -3)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_sends_to_each_member_with_email(self, fake_sender):
        make_member("+12025550203")
        make_member("+12025550204")
        make_event("potluck", 2)
        make_event("film night", 5)
        call_command("send_weekly_digest")
        assert fake_sender.send.call_count == 2

    def test_uses_bulk_email_stream(self, fake_sender, monkeypatch):
        """The digest fans out to every member — it must not spend transactional quota."""

        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        make_member("+12025550250")
        make_event("park cleanup", 2)
        call_command("send_weekly_digest")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_to_sends_single_digest_to_that_address(self, fake_sender):
        make_member("+12025550260")
        make_member("+12025550261")
        make_event("potluck", 2)
        call_command("send_weekly_digest", to="probe@example.com")
        assert fake_sender.send.call_count == 1
        assert fake_sender.send.call_args.kwargs["to"] == "probe@example.com"

    def test_to_uses_first_name_of_matching_user(self, fake_sender):
        make_member("+12025550262", email="known@example.com")
        make_event("potluck", 2)
        call_command("send_weekly_digest", to="known@example.com")
        assert "hi test" in fake_sender.send.call_args.kwargs["text"]

    def test_to_raises_when_send_fails(self, fake_sender):
        fake_sender.send.return_value = SendResult(
            success=False, error="http 401 code=unauthorized"
        )
        make_event("potluck", 2)
        with pytest.raises(CommandError, match="unauthorized"):
            call_command("send_weekly_digest", to="probe@example.com")

    def test_to_still_uses_bulk_stream(self, fake_sender, monkeypatch):

        spy = MagicMock(return_value=fake_sender)
        monkeypatch.setattr(digest_command, "get_email_sender", spy)
        make_event("potluck", 2)
        call_command("send_weekly_digest", to="probe@example.com")
        assert spy.call_args.args[0] is EmailStream.BULK

    def test_digest_lists_both_events(self, fake_sender):
        make_member("+12025550205")
        make_event("potluck", 2)
        make_event("film night", 5)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "potluck" in text
        assert "film night" in text

    def test_skips_member_with_no_email(self, fake_sender):
        make_member("+12025550206", email="")
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_cancelled_and_deleted_events(self, fake_sender):
        make_member("+12025550207")
        make_event("cancelled potluck", 2, status=EventStatus.CANCELLED)
        make_event("deleted potluck", 3, status=EventStatus.DELETED)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_soft_deleted_event(self, fake_sender):
        make_member("+12025550208")
        make_event("removed potluck", 2, deleted_at=timezone.now())
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_includes_official_and_club_events(self, fake_sender):
        make_member("+12025550213")
        make_event("official meetup", 2, event_type=EventType.OFFICIAL)
        make_event("book club", 3, event_type=EventType.CLUB)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "official meetup" in text
        assert "book club" in text

    def test_excludes_community_events(self, fake_sender):
        make_member("+12025550214")
        make_event("random hangout", 2, event_type=EventType.COMMUNITY)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_excludes_non_member(self, fake_sender):
        User.objects.create_user(
            phone_number="+12025550209",
            password="testpass123",
            email="guest@example.test",
            is_member=False,
        )
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_member_opted_out(self, fake_sender):
        make_member("+12025550210", weekly_digest_opt_out=True)
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_paused_member(self, fake_sender):
        make_member("+12025550212", is_paused=True)
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_email_links_to_settings(self, fake_sender):
        make_member("+12025550211")
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "/settings" in text

    def test_counts_failed_sends_separately(self, fake_sender):
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        make_member("+12025550215")
        make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 0 digest(s); 1 failed." in out.getvalue()

    def test_reports_zero_failures_on_success(self, fake_sender):
        make_member("+12025550216")
        make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 digest(s); 0 failed." in out.getvalue()

    def test_counts_mixed_success_and_failure(self, fake_sender):
        fake_sender.send.side_effect = [
            SendResult(success=True, provider_message_id="test_msg"),
            SendResult(success=False, error="boom"),
        ]
        make_member("+12025550217")
        make_member("+12025550218")
        make_event("potluck", 2)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 digest(s); 1 failed." in out.getvalue()

    def test_formats_event_time_in_eastern_not_utc(self, fake_sender):
        make_member("+12025550219")
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

    def test_omits_veganniversaries(self, fake_sender, monkeypatch):
        _freeze_digest(monkeypatch, datetime(2026, 6, 3, 12, 0, 0))
        make_member(
            "+12025550220",
            first_name="Ada",
            veganniversary_month=6,
            veganniversary_year=2021,
            veganniversary_shoutout_opt_in=True,
        )
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        kwargs = fake_sender.send.call_args.kwargs
        assert "veganniversary" not in kwargs["text"]
        assert "veganniversary" not in kwargs["html"]


@pytest.mark.django_db
class TestWeeklyDigestTentativeMembers:
    def test_sends_to_tentative_member(self, fake_sender):
        tentative = make_tentative("+12025550270")
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_called_once()
        assert fake_sender.send.call_args.kwargs["to"] == tentative.email

    def test_skips_tentative_member_opted_out(self, fake_sender):
        make_tentative("+12025550271", weekly_digest_opt_out=True)
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()

    def test_skips_paused_tentative_member(self, fake_sender):
        make_tentative("+12025550272", is_paused=True)
        make_event("potluck", 2)
        call_command("send_weekly_digest")
        fake_sender.send.assert_not_called()
