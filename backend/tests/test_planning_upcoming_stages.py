from datetime import date, datetime

import pytest
from community.models import AssignmentStatus, SlotAssignment
from community.planning.reminders import send_upcoming_notices, upcoming_stage
from django.conf import settings
from notifications.models import Notification
from users.permissions import PermissionKey

from tests._events import make_event
from tests._users import make_user

PROPOSED_AT = datetime(2026, 11, 1, 15, 0, tzinfo=settings.COMMUNITY_TZ)


def _at(month, day, year=2026):
    return datetime(year, month, day, 9, 0, tzinfo=settings.COMMUNITY_TZ)


@pytest.fixture
def february(year):
    return year.slots.get(label="february")


@pytest.fixture
def committed(february):
    planner = make_user(PermissionKey.VIEW_EVENT_PLANNING, email="feb@example.com")
    return SlotAssignment.objects.create(
        slot=february, user=planner, status=AssignmentStatus.COMMITTED, proposed_at=PROPOSED_AT
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("label", "today", "stage"),
    [
        ("february", date(2026, 11, 30), None),
        ("february", date(2026, 12, 1), date(2026, 12, 1)),
        ("february", date(2026, 12, 20), date(2026, 12, 15)),
        ("february", date(2026, 12, 27), date(2026, 12, 21)),
        ("february", date(2026, 12, 28), date(2026, 12, 28)),
        ("february", date(2027, 1, 15), date(2026, 12, 30)),
        ("april", date(2027, 2, 26), date(2027, 2, 25)),
        ("january", date(2026, 12, 12), date(2026, 12, 11)),
        ("january", date(2026, 12, 20), date(2026, 12, 13)),
    ],
)
def test_upcoming_stage(year, label, today, stage):
    assert upcoming_stage(year.slots.get(label=label), today) == stage


@pytest.mark.django_db
class TestUpcomingStages:
    def test_sends_on_each_stage_and_not_between(self, committed, fake_email_sender):
        for day in (1, 15, 21, 28, 30):
            assert send_upcoming_notices(_at(12, day)) == 1
            assert send_upcoming_notices(_at(12, day)) == 0
        for day in (2, 14, 22, 29, 31):
            assert send_upcoming_notices(_at(12, day)) == 0
        assert Notification.objects.count() == 5

    def test_first_says_coming_up_later_ones_say_still_needs_an_event(
        self, committed, fake_email_sender
    ):
        send_upcoming_notices(_at(12, 1))
        first = fake_email_sender.send.call_args.kwargs
        assert first["subject"] == "february is coming up: create the event by dec 31"
        assert "by dec 31 so it's in the jan 1 announcement" in first["text"]
        send_upcoming_notices(_at(12, 15))
        later = fake_email_sender.send.call_args.kwargs
        assert later["subject"] == "february still needs an event: it's due dec 31"
        assert "still doesn't have an event on the calendar" in later["text"]
        assert "create the event" in later["html"]
        assert Notification.objects.order_by("created_at").last().message == (
            "february still needs an event — it's due dec 31"
        )

    def test_missed_runs_send_only_the_latest_stage(self, committed, fake_email_sender):
        assert send_upcoming_notices(_at(12, 22)) == 1
        assert send_upcoming_notices(_at(12, 27)) == 0
        assert fake_email_sender.send.call_count == 1

    def test_stops_once_the_event_exists(self, committed, february, fake_email_sender):
        assert send_upcoming_notices(_at(12, 1)) == 1
        february.event = make_event()
        february.save(update_fields=["event"])
        assert send_upcoming_notices(_at(12, 15)) == 0

    def test_late_commit_after_due_gets_one_notice(self, committed, fake_email_sender):
        assert send_upcoming_notices(_at(1, 10, year=2027)) == 1
        assert send_upcoming_notices(_at(1, 20, year=2027)) == 0
        assert "coming up" in fake_email_sender.send.call_args.kwargs["subject"]
