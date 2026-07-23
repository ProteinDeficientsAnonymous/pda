import pytest
from community.models import Event, EventStatus, EventType, FeatureFlag, FeatureFlagState
from django.core.management import call_command
from django.utils import timezone


@pytest.mark.django_db
def test_command_noop_when_flag_off(test_user, fake_email_sender, capsys):
    Event.objects.create(
        title="Club Meetup",
        event_type=EventType.CLUB,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        start_datetime=timezone.now(),
        created_by=test_user,
    )
    call_command("send_checkin_nudges")
    assert "Sent 0 check-in nudge(s)" in capsys.readouterr().out


@pytest.mark.django_db
def test_command_sends_when_flag_on(test_user, fake_email_sender, capsys):
    FeatureFlagState.objects.create(key=FeatureFlag.HOST_ATTENDANCE_REPORT, enabled=True)
    event = Event.objects.create(
        title="Club Meetup",
        event_type=EventType.CLUB,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        start_datetime=timezone.now(),
        created_by=test_user,
    )
    call_command("send_checkin_nudges")
    assert "Sent 1 check-in nudge(s)" in capsys.readouterr().out
    event.refresh_from_db()
    assert event.checkin_nudge_sent_at is not None
