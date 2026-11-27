from datetime import datetime

import pytest
from community.clubs.reminders import send_club_event_reminders
from community.models import (
    Club,
    ClubEventReminder,
    ClubReminderStage,
    Event,
    EventStatus,
    EventType,
)
from django.conf import settings
from django.core.management import call_command

from tests._users import make_attendance_paused, make_user


def _now(y, m, d):
    return datetime(y, m, d, 12, tzinfo=settings.COMMUNITY_TZ)


def _club(name="book club", *reps):
    club = Club.objects.create(name=name)
    club.reps.add(*reps)
    return club


def _cover(club, y=2026, m=12):
    Event.objects.create(
        title="e",
        club=club,
        event_type=EventType.CLUB,
        status=EventStatus.ACTIVE,
        start_datetime=datetime(y, m, 5, 12, tzinfo=settings.COMMUNITY_TZ),
    )


def _sent(fake):
    return [c.kwargs for c in fake.send.call_args_list]


@pytest.mark.django_db
def test_emails_every_active_rep_of_uncovered_club(fake_email_sender):
    a, b = make_user(email="a@example.test"), make_user(email="b@example.test")
    _club("book club", a, b)
    assert send_club_event_reminders(_now(2026, 11, 10)) == 2
    sent = _sent(fake_email_sender)
    assert {s["to"] for s in sent} == {"a@example.test", "b@example.test"}
    assert {s["subject"] for s in sent} == {"december book club events get shared on the 15th"}
    assert "book club" in sent[0]["text"]
    assert "/events/add" in sent[0]["html"]


@pytest.mark.django_db
def test_skips_paused_archived_and_emailless_reps(fake_email_sender):
    ok = make_user(email="ok@example.test")
    paused = make_attendance_paused()
    archived = make_user()
    archived.save(update_fields=archived.archive(by=None))
    no_email = make_user(email="")
    _club("book club", ok, paused, archived, no_email)
    assert send_club_event_reminders(_now(2026, 11, 10)) == 1
    assert [s["to"] for s in _sent(fake_email_sender)] == ["ok@example.test"]


@pytest.mark.django_db
def test_covered_club_gets_nothing(fake_email_sender):
    _cover(_club("book club", make_user()))
    assert send_club_event_reminders(_now(2026, 11, 10)) == 0
    fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
def test_rep_of_two_clubs_one_covered_gets_one_email_and_rerun_sends_none(fake_email_sender):
    rep = make_user()
    _cover(_club("a club", rep))
    _club("b club", rep)
    assert send_club_event_reminders(_now(2026, 11, 10)) == 1
    assert send_club_event_reminders(_now(2026, 11, 10)) == 0
    assert fake_email_sender.send.call_count == 1


@pytest.mark.django_db
def test_missed_day_catches_up_with_latest_stage_only(fake_email_sender):
    _club("book club", make_user())
    assert send_club_event_reminders(_now(2026, 11, 24)) == 1
    stages = list(ClubEventReminder.objects.values_list("stage", flat=True))
    assert stages == [ClubReminderStage.WEEK]
    assert _sent(fake_email_sender)[0]["subject"] == "book club: december events due by nov 30"


@pytest.mark.django_db
def test_nothing_sent_on_the_9th(fake_email_sender):
    _club("book club", make_user())
    assert send_club_event_reminders(_now(2026, 11, 9)) == 0
    fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
def test_final_subject(fake_email_sender):
    _club("book club", make_user())
    send_club_event_reminders(_now(2026, 11, 30))
    assert _sent(fake_email_sender)[0]["subject"] == "book club: december events due today"


@pytest.mark.django_db
def test_command_runs(fake_email_sender):
    call_command("send_club_event_reminders")


@pytest.mark.django_db
def test_club_with_only_emailless_reps_sends_nothing_but_records_reminder(fake_email_sender):
    _club("book club", make_user(email=""))
    assert send_club_event_reminders(_now(2026, 11, 10)) == 0
    fake_email_sender.send.assert_not_called()
    assert ClubEventReminder.objects.count() == 1


@pytest.mark.django_db
def test_catch_up_after_the_15th_uses_week_style_subject(fake_email_sender):
    _club("book club", make_user())
    assert send_club_event_reminders(_now(2026, 11, 17)) == 1
    assert list(ClubEventReminder.objects.values_list("stage", flat=True)) == [
        ClubReminderStage.EARLY
    ]
    assert _sent(fake_email_sender)[0]["subject"] == "book club: december events due by nov 30"
