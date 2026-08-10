"""Tests for the send_weekly_digest management command."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from community.models import Event, EventStatus
from django.core.management import call_command
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import User


def _make_member(phone_number: str, **extra) -> User:
    return User.objects.create_user(
        phone_number=phone_number,
        password="testpass123",
        first_name="Test",
        email=extra.pop("email", f"{phone_number}@example.test"),
        is_member=True,
        **extra,
    )


def _make_event(title: str, days_out: float, **extra) -> Event:
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
    monkeypatch.setattr(email_sender_module, "_cached_sender", fake)
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

    def test_email_links_to_settings(self, fake_sender):
        _make_member("+12025550211")
        _make_event("potluck", 2)
        call_command("send_weekly_digest")
        text = fake_sender.send.call_args.kwargs["text"]
        assert "/settings" in text
