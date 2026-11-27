from datetime import datetime, timedelta

import pytest
from community.management.commands import send_event_updates as command
from community.models import Club, Event, EventType
from django.core.management import call_command
from django.utils import timezone
from notifications.email_sender import SendResult
from users.permissions import PermissionKey
from users.roles import Role

from tests._users import make_user

pytestmark = pytest.mark.django_db

NOW = timezone.make_aware(datetime(2026, 11, 14, 12, 0))


def test_command_emails_permission_holders_on_update_days(fake_email_sender, monkeypatch):
    poster = make_user(PermissionKey.SEND_EVENT_UPDATES, first_name="Sam")
    make_user().roles.add(Role.objects.get(name="admin", is_default=True))
    Club.objects.create(name="Book Club")
    start = NOW + timedelta(days=3)
    Event.objects.create(title="Holiday Party", start_datetime=start, event_type=EventType.OFFICIAL)
    monkeypatch.setattr(command.timezone, "now", lambda: NOW + timedelta(days=1))
    call_command("send_event_updates")
    fake_email_sender.send.assert_not_called()

    monkeypatch.setattr(command.timezone, "now", lambda: NOW)
    call_command("send_event_updates")
    fake_email_sender.send.assert_called_once()
    kwargs = fake_email_sender.send.call_args.kwargs
    assert kwargs["to"] == poster.email
    assert "- Book Club" in kwargs["text"] and "11/17 Holiday Party" in kwargs["text"]
    assert "Book Club" in kwargs["html"]


def test_command_rerun_retries_only_failures(fake_email_sender, monkeypatch):
    first = make_user(PermissionKey.SEND_EVENT_UPDATES)
    second = make_user(PermissionKey.SEND_EVENT_UPDATES)
    monkeypatch.setattr(command.timezone, "now", lambda: NOW)
    sends = {first.email: RuntimeError("provider down"), second.email: None}

    def send(**kwargs):
        if error := sends[kwargs["to"]]:
            raise error
        return SendResult(success=True, provider_message_id="m")

    fake_email_sender.send.side_effect = send
    call_command("send_event_updates")
    tried = {c.kwargs["to"] for c in fake_email_sender.send.call_args_list}
    assert tried == {first.email, second.email}

    sends[first.email] = None
    fake_email_sender.send.reset_mock()
    call_command("send_event_updates")
    assert [c.kwargs["to"] for c in fake_email_sender.send.call_args_list] == [first.email]
