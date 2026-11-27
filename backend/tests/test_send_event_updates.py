from datetime import datetime, timedelta

import pytest
from community.management.commands import send_event_updates as command
from community.models import Club, Event, EventType
from django.core.management import call_command
from django.utils import timezone
from users.permissions import PermissionKey

from tests._users import make_user

pytestmark = pytest.mark.django_db

NOW = timezone.make_aware(datetime(2026, 11, 14, 12, 0))


def test_command_emails_permission_holders_on_update_days(fake_email_sender, monkeypatch):
    poster = make_user(PermissionKey.SEND_EVENT_UPDATES, first_name="Sam")
    make_user()
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
