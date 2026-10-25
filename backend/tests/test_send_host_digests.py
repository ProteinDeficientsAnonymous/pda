from datetime import timedelta
from io import StringIO
from itertools import count
from unittest.mock import MagicMock

import pytest
from community.management.commands import send_host_digests as command_module
from community.models import Event, EventRSVP, RSVPStatus
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import User

pytestmark = pytest.mark.django_db

HOUR = timedelta(hours=1)
_phones = count(600)


@pytest.fixture
def run_at(monkeypatch):
    frozen = timezone.now()
    monkeypatch.setattr(
        "community.management.commands.send_host_digests.timezone.now", lambda: frozen
    )
    return frozen


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


def _user(first: str) -> User:
    phone = f"+1202555{next(_phones):04d}"
    return User.objects.create_user(
        phone_number=phone, password="pw", first_name=first, email=f"{phone[1:]}@example.test"
    )


def _event(host: User, title: str) -> Event:
    return Event.objects.create(title=title, created_by=host, rsvp_enabled=True)


def _rsvp(event: Event, user: User, at) -> None:
    rsvp = EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.filter(pk=rsvp.pk).update(status_changed_at=at)


def _run(*args: str) -> str:
    out = StringIO()
    call_command("send_host_digests", *args, stdout=out)
    return out.getvalue()


def test_one_email_per_host_then_watermark_blocks_resend(run_at, fake_sender):
    host, cohost = _user("host"), _user("cohost")
    hike = _event(host, "hike")
    hike.co_hosts.add(cohost)
    _rsvp(hike, _user("sam"), run_at - HOUR)
    _rsvp(_event(host, "potluck"), _user("alex"), run_at - HOUR)

    _run()
    _run()

    assert fake_sender.send.call_count == 2
    sent = {c.kwargs["to"]: c.kwargs["text"] for c in fake_sender.send.call_args_list}
    assert "hike" in sent[host.email]
    assert "potluck" in sent[host.email]
    assert "potluck" not in sent[cohost.email]
    host.refresh_from_db()
    assert host.host_digest_last_sent_at == run_at


def test_failures_keep_watermark_without_stopping_the_run(run_at, fake_sender, monkeypatch):
    fake_sender.send.return_value = SendResult(success=False, error="x")
    failing, broken, idle = _user("failing"), _user("broken"), _user("idle")
    _rsvp(_event(failing, "hike"), _user("sam"), run_at - HOUR)
    _rsvp(_event(broken, "picnic"), _user("alex"), run_at - HOUR)
    _event(idle, "potluck")
    real_build = command_module.build_host_digest

    def flaky_build(host, at):
        if host.pk == broken.pk:
            raise RuntimeError("boom")
        return real_build(host, at)

    monkeypatch.setattr(command_module, "build_host_digest", flaky_build)

    out = _run()

    stamps = dict(User.objects.values_list("first_name", "host_digest_last_sent_at"))
    assert (stamps["failing"], stamps["broken"], stamps["idle"]) == (None, None, run_at)
    assert [c.kwargs["to"] for c in fake_sender.send.call_args_list] == [failing.email]
    assert "2 failed; 1 with no activity" in out


def test_dry_run_sends_and_writes_nothing(run_at, fake_sender):
    host = _user("host")
    _rsvp(_event(host, "hike"), _user("sam"), run_at - HOUR)

    out = _run("--dry-run")

    host.refresh_from_db()
    assert fake_sender.send.call_count == 0
    assert host.host_digest_last_sent_at is None
    assert "hike" in out
    assert host.email not in out


def test_cron_daily_runs_command():
    cron = (settings.BASE_DIR.parent / "scripts" / "cron_daily.sh").read_text()
    assert "manage.py send_host_digests" in cron
