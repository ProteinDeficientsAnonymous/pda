"""Tests for the weekly login reminder sent before the weekly digest."""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from community import _login_reminder as login_reminder
from community.management.commands import send_weekly_digest as digest_command
from community.models import Event, EventType, JoinRequest, JoinRequestStatus, LoginReminder
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import EmailStream, SendResult
from users.models import MagicLoginToken, MagicLoginTokenSource, User

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


def _make_event() -> None:
    Event.objects.create(
        title="potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() + timedelta(days=2),
    )


def _reminder_calls(fake_sender) -> list:
    return [c for c in fake_sender.send.call_args_list if c.kwargs["subject"] == REMINDER_SUBJECT]


def _token_in(call) -> str:
    return call.kwargs["text"].split("/magic-login/")[1].split()[0]


def _old_admin_link(user: User) -> MagicLoginToken:
    link = MagicLoginToken.create_for_user(user)
    MagicLoginToken.objects.filter(pk=link.pk).update(created_at=timezone.now() - timedelta(days=7))
    return link


def _run_weekly(weeks: int) -> None:
    for _ in range(weeks):
        call_command("send_weekly_digest")
        LoginReminder.objects.update(sent_at=F("sent_at") - timedelta(days=7))


@pytest.mark.django_db
class TestWeeklyLoginReminder:
    def test_reminds_member_who_never_logged_in(self, fake_email_sender):
        user = _make_pending_member("+12025550301")
        call_command("send_weekly_digest")
        calls = _reminder_calls(fake_email_sender)
        assert len(calls) == 1
        assert calls[0].kwargs["to"] == user.email
        assert calls[0].kwargs["subject"] == REMINDER_SUBJECT

    def test_reminds_tentative_member_who_never_logged_in(self, fake_email_sender):
        user = _make_pending_tentative("+12025550302")
        call_command("send_weekly_digest")
        assert [c.kwargs["to"] for c in _reminder_calls(fake_email_sender)] == [user.email]

    def test_sends_even_when_digest_has_nothing_to_send(self, fake_email_sender):
        _make_pending_member("+12025550303")
        call_command("send_weekly_digest")
        assert fake_email_sender.send.call_count == 1
        assert len(_reminder_calls(fake_email_sender)) == 1

    def test_sends_alongside_digest_when_there_are_events(self, fake_email_sender):
        _make_pending_member("+12025550304")
        _make_event()
        call_command("send_weekly_digest")
        assert fake_email_sender.send.call_count == 2
        assert len(_reminder_calls(fake_email_sender)) == 1

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
    def test_skips_users_who_should_not_be_reminded(self, fake_email_sender, extra):
        _make_pending_member("+12025550305", **extra)
        call_command("send_weekly_digest")
        assert _reminder_calls(fake_email_sender) == []

    def test_link_is_a_fresh_reminder_token(self, fake_email_sender):
        user = _make_pending_member("+12025550306")
        call_command("send_weekly_digest")
        token = MagicLoginToken.objects.get(user=user)
        assert not token.used
        assert not token.is_expired
        assert token.source == MagicLoginTokenSource.REMINDER
        assert _token_in(_reminder_calls(fake_email_sender)[0]) == str(token.token)

    def test_invalidates_earlier_reminder_links(self, fake_email_sender):
        user = _make_pending_member("+12025550307")
        _run_weekly(1)
        call_command("send_weekly_digest")
        tokens = MagicLoginToken.objects.filter(user=user, source=MagicLoginTokenSource.REMINDER)
        assert tokens.count() == 2
        assert tokens.filter(used=False).count() == 1

    def test_keeps_admin_links_working(self, fake_email_sender):
        user = _make_pending_member("+12025550316")
        admin_link = _old_admin_link(user)
        call_command("send_weekly_digest")
        admin_link.refresh_from_db()
        assert len(_reminder_calls(fake_email_sender)) == 1
        assert not admin_link.used

    def test_skips_member_with_a_recent_admin_link(self, fake_email_sender):
        user = _make_pending_member("+12025550317")
        MagicLoginToken.create_for_user(user)
        call_command("send_weekly_digest")
        assert _reminder_calls(fake_email_sender) == []

    def test_skips_legacy_member_mid_password_reset(self, fake_email_sender):
        user = _make_pending_member("+12025550318", last_login=timezone.now() - timedelta(days=90))
        User.objects.filter(pk=user.pk).update(created_at=datetime(2026, 1, 1, tzinfo=UTC))
        call_command("send_weekly_digest")
        assert _reminder_calls(fake_email_sender) == []

    def test_reminds_member_who_opened_a_link_but_never_finished_setup(
        self, api_client, fake_email_sender
    ):
        _make_pending_member("+12025550319")
        _run_weekly(1)
        token = _token_in(_reminder_calls(fake_email_sender)[0])
        assert api_client.get(f"/api/auth/magic-login/{token}/").status_code == 200
        call_command("send_weekly_digest")
        assert len(_reminder_calls(fake_email_sender)) == 2

    def test_failed_send_keeps_earlier_links_and_burns_its_own(self, fake_email_sender):
        user = _make_pending_member("+12025550308")
        earlier = _old_admin_link(user)
        fake_email_sender.send.return_value = SendResult(success=False, error="rejected")
        call_command("send_weekly_digest")
        earlier.refresh_from_db()
        assert not earlier.used
        assert MagicLoginToken.objects.get(user=user, source=MagicLoginTokenSource.REMINDER).used
        assert not LoginReminder.objects.filter(user=user).exists()

    def test_failed_send_is_retried_on_rerun(self, fake_email_sender):
        _make_pending_member("+12025550309")
        fake_email_sender.send.return_value = SendResult(success=False, error="rejected")
        call_command("send_weekly_digest")
        fake_email_sender.send.return_value = SendResult(success=True, provider_message_id="ok")
        call_command("send_weekly_digest")
        assert LoginReminder.objects.count() == 1

    def test_rerun_in_the_same_week_does_not_resend(self, fake_email_sender):
        user = _make_pending_member("+12025550310")
        call_command("send_weekly_digest")
        call_command("send_weekly_digest")
        assert len(_reminder_calls(fake_email_sender)) == 1
        assert MagicLoginToken.objects.filter(user=user).count() == 1

    def test_to_flag_skips_reminders(self, fake_email_sender):
        _make_pending_member("+12025550311")
        _make_event()
        call_command("send_weekly_digest", to="probe@example.com")
        assert _reminder_calls(fake_email_sender) == []

    def test_reports_sent_and_failed_counts(self, fake_email_sender):
        _make_pending_member("+12025550312")
        _make_pending_member("+12025550313")
        fake_email_sender.send.side_effect = [
            SendResult(success=True, provider_message_id="ok"),
            SendResult(success=False, error="boom"),
        ]
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 1 login reminder(s); 1 failed." in out.getvalue()

    def test_sends_reminders_even_when_the_digest_fails(self, fake_email_sender, monkeypatch):
        _make_pending_member("+12025550314")
        _make_event()

        def fail(**_kwargs):
            raise RuntimeError("digest template broke")

        monkeypatch.setattr(digest_command, "send_weekly_digest_email", fail)
        with pytest.raises(RuntimeError):
            call_command("send_weekly_digest")
        assert len(_reminder_calls(fake_email_sender)) == 1

    def test_sends_the_digest_even_when_reminders_fail(self, fake_email_sender, monkeypatch):
        _make_pending_member("+12025550320")
        _make_event()
        User.objects.create(phone_number="+12025550321", email="m@example.test", is_member=True)

        def fail(**_kwargs):
            raise RuntimeError("reminder template broke")

        monkeypatch.setattr(login_reminder, "send_magic_login_email", fail)
        err = StringIO()
        call_command("send_weekly_digest", stderr=err)
        assert "Login reminders failed" in err.getvalue()
        assert _reminder_calls(fake_email_sender) == []
        assert fake_email_sender.send.call_count == 2

    def test_overlapping_run_does_not_send_twice(self, fake_email_sender):
        user = _make_pending_member("+12025550322")
        now = timezone.now()
        stale_list = login_reminder._users_to_remind(now)
        call_command("send_weekly_digest")
        assert login_reminder._claim(stale_list[0], now) is None
        assert LoginReminder.objects.filter(user=user).count() == 1

    def test_uses_the_transactional_sender(self, monkeypatch):
        transactional, bulk = MagicMock(), MagicMock()
        transactional.send.return_value = SendResult(success=True, provider_message_id="ok")
        monkeypatch.setattr(
            email_sender_module,
            "_cached_senders",
            {EmailStream.TRANSACTIONAL: transactional, EmailStream.BULK: bulk},
        )
        _make_pending_member("+12025550315")
        call_command("send_weekly_digest")
        assert len(_reminder_calls(transactional)) == 1
        assert _reminder_calls(bulk) == []


@pytest.mark.django_db
class TestOngoingReminders:
    def test_reminds_weekly_four_times_then_monthly_without_archiving(self, fake_email_sender):
        user = _make_pending_member("+12025550401")
        _run_weekly(4)
        assert len(_reminder_calls(fake_email_sender)) == 4
        _run_weekly(3)
        assert len(_reminder_calls(fake_email_sender)) == 4
        _run_weekly(1)
        assert len(_reminder_calls(fake_email_sender)) == 5
        _run_weekly(4)
        assert len(_reminder_calls(fake_email_sender)) == 6
        user.refresh_from_db()
        assert user.archived_at is None
        assert not user.is_paused

    def test_stops_once_member_finishes_setup(self, fake_email_sender):
        user = _make_pending_member("+12025550402")
        _run_weekly(2)
        User.objects.filter(pk=user.pk).update(needs_onboarding=False, onboarded_at=timezone.now())
        _run_weekly(1)
        assert len(_reminder_calls(fake_email_sender)) == 2


@pytest.mark.django_db
class TestAdminLinkReuse:
    def test_admin_regenerate_does_not_reuse_a_reminder_token(
        self, api_client, manage_users_headers, fake_email_sender
    ):
        user = _make_pending_member("+12025550501")
        call_command("send_weekly_digest")
        reminder_token = _token_in(_reminder_calls(fake_email_sender)[0])
        response = api_client.post(f"/api/auth/users/{user.pk}/magic-link/", **manage_users_headers)
        assert response.status_code == 200
        assert response.json()["magic_link_token"] != reminder_token
        assert "already generated" not in response.json()["detail"]
