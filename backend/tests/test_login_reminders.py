"""Tests for the weekly login reminder sent before the weekly digest."""

from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from community.management.commands import send_weekly_digest as digest_command
from community.models import Event, EventType, JoinRequest, JoinRequestStatus, LoginReminder
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import EmailStream, SendResult
from users.models import MagicLoginToken, MagicLoginTokenSource, User

REMINDER_SUBJECT = "finish setting up your pda account"
FINAL_SUBJECT = "last reminder: set up your pda account or lose your membership"


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
    return [
        c
        for c in fake_sender.send.call_args_list
        if c.kwargs["subject"] in (REMINDER_SUBJECT, FINAL_SUBJECT)
    ]


def _token_in(call) -> str:
    return call.kwargs["text"].split("/magic-login/")[1].split()[0]


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

    def test_invalidates_earlier_login_links(self, fake_email_sender):
        user = _make_pending_member("+12025550307")
        earlier = MagicLoginToken.create_for_user(user)
        call_command("send_weekly_digest")
        earlier.refresh_from_db()
        assert earlier.used
        assert MagicLoginToken.objects.filter(user=user, used=False).count() == 1

    def test_failed_send_keeps_earlier_links_and_burns_its_own(self, fake_email_sender):
        user = _make_pending_member("+12025550308")
        earlier = MagicLoginToken.create_for_user(user)
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
        assert "Sent 1 login reminder(s); 1 failed; archived 0 member(s)." in out.getvalue()

    def test_sends_reminders_even_when_the_digest_fails(self, fake_email_sender, monkeypatch):
        _make_pending_member("+12025550314")
        _make_event()

        def fail(**_kwargs):
            raise RuntimeError("digest template broke")

        monkeypatch.setattr(digest_command, "send_weekly_digest_email", fail)
        with pytest.raises(RuntimeError):
            call_command("send_weekly_digest")
        assert len(_reminder_calls(fake_email_sender)) == 1

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
class TestLoginReminderCap:
    def test_fourth_reminder_is_the_final_warning(self, fake_email_sender):
        _make_pending_member("+12025550401")
        _run_weekly(4)
        calls = _reminder_calls(fake_email_sender)
        assert [c.kwargs["subject"] for c in calls] == [REMINDER_SUBJECT] * 3 + [FINAL_SUBJECT]
        assert "we'll remove your pda membership" in calls[-1].kwargs["text"]

    def test_archives_a_week_after_the_final_warning(self, fake_email_sender):
        user = _make_pending_member("+12025550402")
        _run_weekly(5)
        user.refresh_from_db()
        assert user.archived_at is not None
        assert len(_reminder_calls(fake_email_sender)) == 4
        assert not LoginReminder.objects.filter(user=user).exists()

    def test_reports_archived_count(self, fake_email_sender):
        _make_pending_member("+12025550403")
        _run_weekly(4)
        out = StringIO()
        call_command("send_weekly_digest", stdout=out)
        assert "Sent 0 login reminder(s); 0 failed; archived 1 member(s)." in out.getvalue()

    def test_does_not_archive_before_a_week_has_passed(self, fake_email_sender):
        user = _make_pending_member("+12025550404")
        _run_weekly(3)
        call_command("send_weekly_digest")
        call_command("send_weekly_digest")
        user.refresh_from_db()
        assert user.archived_at is None

    def test_whatsapp_member_is_never_warned_or_archived(self, fake_email_sender):
        user = _make_pending_member("+12025550405", has_joined_whatsapp=True)
        _run_weekly(6)
        user.refresh_from_db()
        assert user.archived_at is None
        subjects = [c.kwargs["subject"] for c in _reminder_calls(fake_email_sender)]
        assert subjects == [REMINDER_SUBJECT] * 4

    def test_member_who_finishes_setup_is_not_archived(self, fake_email_sender):
        user = _make_pending_member("+12025550406")
        _run_weekly(4)
        User.objects.filter(pk=user.pk).update(needs_onboarding=False, onboarded_at=timezone.now())
        _run_weekly(1)
        user.refresh_from_db()
        assert user.archived_at is None

    def test_reapproved_member_starts_a_fresh_cycle(self, fake_email_sender):
        user = _make_pending_member("+12025550407")
        _run_weekly(5)
        User.objects.filter(pk=user.pk).update(archived_at=None)
        fake_email_sender.send.reset_mock()
        _run_weekly(1)
        user.refresh_from_db()
        assert user.archived_at is None
        assert [c.kwargs["subject"] for c in _reminder_calls(fake_email_sender)] == [
            REMINDER_SUBJECT
        ]


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
