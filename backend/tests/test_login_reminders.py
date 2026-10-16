"""Tests for the weekly login reminder sent alongside the weekly digest."""

from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from community.models import Event, EventType, JoinRequest, JoinRequestStatus
from django.core.management import call_command
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import MagicLoginToken, User

REMINDER_SUBJECT = "finish setting up your pda account"


def _make_pending_member(phone_number: str, **extra) -> User:
    extra.setdefault("email", f"{phone_number}@example.test")
    extra.setdefault("first_name", "Sprout")
    extra.setdefault("is_member", True)
    extra.setdefault("needs_onboarding", True)
    return User.objects.create(phone_number=phone_number, **extra)


def _make_pending_tentative(phone_number: str) -> User:
    user = _make_pending_member(phone_number, is_member=False)
    JoinRequest.objects.create(
        first_name="Sprout",
        phone_number=phone_number,
        email=user.email,
        user=user,
        status=JoinRequestStatus.TENTATIVE,
    )
    return user


def _reminder_calls(fake_sender) -> list:
    return [c for c in fake_sender.send.call_args_list if c.kwargs["subject"] == REMINDER_SUBJECT]


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
class TestWeeklyLoginReminder:
    def test_reminds_member_who_never_logged_in(self, fake_sender):
        user = _make_pending_member("+12025550301")
        call_command("send_weekly_digest")
        calls = _reminder_calls(fake_sender)
        assert len(calls) == 1
        assert calls[0].kwargs["to"] == user.email

    def test_reminds_tentative_member_who_never_logged_in(self, fake_sender):
        user = _make_pending_tentative("+12025550302")
        call_command("send_weekly_digest")
        assert [c.kwargs["to"] for c in _reminder_calls(fake_sender)] == [user.email]

    def test_sends_even_when_digest_has_nothing_to_send(self, fake_sender):
        _make_pending_member("+12025550303")
        call_command("send_weekly_digest")
        assert fake_sender.send.call_count == 1
        assert len(_reminder_calls(fake_sender)) == 1

    def test_sends_alongside_digest_when_there_are_events(self, fake_sender):
        _make_pending_member("+12025550304")
        Event.objects.create(
            title="potluck",
            event_type=EventType.OFFICIAL,
            start_datetime=timezone.now() + timedelta(days=2),
        )
        call_command("send_weekly_digest")
        assert fake_sender.send.call_count == 2
        assert len(_reminder_calls(fake_sender)) == 1

    @pytest.mark.parametrize(
        "extra",
        [
            {"needs_onboarding": False},
            {"onboarded_at": timezone.now()},
            {"archived_at": timezone.now()},
            {"is_paused": True},
            {"is_active": False},
            {"email": ""},
            {"email": None},
            {"is_member": False},
        ],
        ids=[
            "onboarded",
            "onboarded_before_reset",
            "archived",
            "paused",
            "inactive",
            "blank_email",
            "no_email",
            "public_rsvp_non_member",
        ],
    )
    def test_skips_users_who_should_not_be_reminded(self, fake_sender, extra):
        _make_pending_member("+12025550305", **extra)
        call_command("send_weekly_digest")
        assert _reminder_calls(fake_sender) == []

    def test_link_is_a_fresh_login_token(self, fake_sender):
        user = _make_pending_member("+12025550306")
        call_command("send_weekly_digest")
        token = MagicLoginToken.objects.get(user=user)
        assert not token.used
        assert not token.is_expired
        assert f"/magic-login/{token.token}" in _reminder_calls(fake_sender)[0].kwargs["text"]

    def test_keeps_earlier_login_links_working(self, fake_sender):
        user = _make_pending_member("+12025550307")
        earlier = MagicLoginToken.create_for_user(user)
        call_command("send_weekly_digest")
        earlier.refresh_from_db()
        assert not earlier.used
        assert MagicLoginToken.objects.filter(user=user).count() == 2

    def test_to_flag_skips_reminders(self, fake_sender):
        _make_pending_member("+12025550308")
        Event.objects.create(
            title="potluck",
            event_type=EventType.OFFICIAL,
            start_datetime=timezone.now() + timedelta(days=2),
        )
        call_command("send_weekly_digest", to="probe@example.com")
        assert _reminder_calls(fake_sender) == []

    def test_reports_sent_and_failed_counts(self, fake_sender):
        _make_pending_member("+12025550309")
        _make_pending_member("+12025550310")
        fake_sender.send.side_effect = [
            SendResult(success=True, provider_message_id="ok"),
            SendResult(success=False, error="boom"),
        ]
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 login reminder(s); 1 failed." in out.getvalue()
