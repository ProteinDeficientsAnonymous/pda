"""Tests for the send_whatsapp_join_reminders management command."""

from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from community._whatsapp_join_reminder import GRACE_DAYS, INTERVAL_DAYS, MAX_REMINDERS
from community.models import (
    FeatureFlag,
    FeatureFlagState,
    WhatsAppJoinReminder,
    WhatsAppLinkConfig,
)
from django.core.management import call_command
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import User

from tests.conftest import set_flag

_WHATSAPP_LINK = "https://chat.whatsapp.com/testinvite"


def _make_member(phone_number: str, *, joined_days_ago: int = 30, **extra) -> User:
    user = User.objects.create_user(
        phone_number=phone_number,
        password="testpass123",
        first_name="Test",
        email=extra.pop("email", f"{phone_number}@example.test"),
        is_member=True,
        **extra,
    )
    created = timezone.now() - timedelta(days=joined_days_ago)
    User.objects.filter(pk=user.pk).update(created_at=created)
    user.refresh_from_db()
    return user


def _record_reminder(user: User, number: int, *, days_ago: int) -> None:
    reminder = WhatsAppJoinReminder.objects.create(user=user, reminder_number=number)
    WhatsAppJoinReminder.objects.filter(pk=reminder.pk).update(
        sent_at=timezone.now() - timedelta(days=days_ago)
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


@pytest.fixture(autouse=True)
def _enable_flag_and_link(db):
    set_flag(FeatureFlag.WHATSAPP_JOIN_REMINDERS)
    config = WhatsAppLinkConfig.get()
    config.link = _WHATSAPP_LINK
    config.save()


@pytest.mark.django_db
class TestGating:
    def test_noop_when_flag_off(self, fake_sender):
        FeatureFlagState.objects.filter(key=FeatureFlag.WHATSAPP_JOIN_REMINDERS).update(
            enabled=False
        )
        _make_member("+12025550301")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()
        assert WhatsAppJoinReminder.objects.count() == 0

    def test_noop_when_no_whatsapp_link_configured(self, fake_sender):
        config = WhatsAppLinkConfig.get()
        config.link = ""
        config.save()
        _make_member("+12025550302")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()
        assert WhatsAppJoinReminder.objects.count() == 0


@pytest.mark.django_db
class TestRecipientSelection:
    def test_sends_to_member_without_whatsapp(self, fake_sender):
        user = _make_member("+12025550310")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_called_once()
        assert WhatsAppJoinReminder.objects.filter(user=user, reminder_number=1).exists()

    def test_excludes_member_already_on_whatsapp(self, fake_sender):
        _make_member("+12025550311", has_joined_whatsapp=True)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_opted_out_member(self, fake_sender):
        _make_member("+12025550312", whatsapp_reminder_opt_out=True)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_member_with_no_email(self, fake_sender):
        _make_member("+12025550313", email="")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_paused_member(self, fake_sender):
        _make_member("+12025550314", is_paused=True)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_archived_member(self, fake_sender):
        _make_member("+12025550315", archived_at=timezone.now())
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_excludes_non_member(self, fake_sender):
        User.objects.create_user(
            phone_number="+12025550316",
            password="testpass123",
            email="guest@example.test",
            is_member=False,
        )
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_skips_member_still_inside_grace_period(self, fake_sender):
        _make_member("+12025550317", joined_days_ago=GRACE_DAYS - 1)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()
        assert WhatsAppJoinReminder.objects.count() == 0


@pytest.mark.django_db
class TestCadence:
    def test_idempotent_second_run_same_day_sends_nothing(self, fake_sender):
        _make_member("+12025550320")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.reset_mock()
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()
        assert WhatsAppJoinReminder.objects.count() == 1

    def test_sends_follow_up_once_interval_elapsed(self, fake_sender):
        user = _make_member("+12025550321")
        _record_reminder(user, 1, days_ago=INTERVAL_DAYS)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_called_once()
        assert WhatsAppJoinReminder.objects.filter(user=user, reminder_number=2).exists()

    def test_no_follow_up_before_interval_elapsed(self, fake_sender):
        user = _make_member("+12025550322")
        _record_reminder(user, 1, days_ago=INTERVAL_DAYS - 1)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()

    def test_stops_after_max_reminders(self, fake_sender):
        user = _make_member("+12025550323", joined_days_ago=365)
        for number in range(1, MAX_REMINDERS + 1):
            _record_reminder(user, number, days_ago=INTERVAL_DAYS * 2)
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()
        assert WhatsAppJoinReminder.objects.filter(user=user).count() == MAX_REMINDERS

    def test_joining_whatsapp_stops_further_reminders(self, fake_sender):
        user = _make_member("+12025550324")
        _record_reminder(user, 1, days_ago=INTERVAL_DAYS)
        user.has_joined_whatsapp = True
        user.save()
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.assert_not_called()


@pytest.mark.django_db
class TestSendFailures:
    def test_failed_send_does_not_record_reminder(self, fake_sender):
        user = _make_member("+12025550330")
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        call_command("send_whatsapp_join_reminders")
        assert not WhatsAppJoinReminder.objects.filter(user=user).exists()

    def test_failed_send_retried_on_next_run(self, fake_sender):
        user = _make_member("+12025550331")
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        call_command("send_whatsapp_join_reminders")
        fake_sender.send.return_value = SendResult(success=True, provider_message_id="msg")
        call_command("send_whatsapp_join_reminders")
        assert WhatsAppJoinReminder.objects.filter(user=user, reminder_number=1).exists()

    def test_counts_failed_sends_separately(self, fake_sender):
        _make_member("+12025550332")
        fake_sender.send.return_value = SendResult(success=False, error="boom")
        out = StringIO()
        call_command("send_whatsapp_join_reminders", stdout=out)
        assert "Sent 0 reminder(s); 1 failed." in out.getvalue()


@pytest.mark.django_db
class TestEmailContent:
    def test_email_includes_whatsapp_link_and_opt_out_link(self, fake_sender):
        _make_member("+12025550340")
        call_command("send_whatsapp_join_reminders")
        kwargs = fake_sender.send.call_args.kwargs
        assert _WHATSAPP_LINK in kwargs["html"]
        assert _WHATSAPP_LINK in kwargs["text"]
        assert "/settings" in kwargs["html"]
        assert "/settings" in kwargs["text"]
        assert "let us know here" in kwargs["html"]
