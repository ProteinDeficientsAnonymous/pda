from datetime import date, datetime

import pytest
from community.clubs.reminders import due_stage, target_month, uncovered_clubs
from community.models import (
    Club,
    ClubEventReminder,
    ClubReminderStage,
    Event,
    EventStatus,
    EventType,
)
from django.conf import settings
from django.db import IntegrityError, transaction

S = ClubReminderStage


@pytest.mark.parametrize(
    ("today", "stage"),
    [
        (date(2026, 11, 9), None),
        (date(2026, 11, 10), S.EARLY),
        (date(2026, 11, 22), S.EARLY),
        (date(2026, 11, 23), S.WEEK),
        (date(2026, 11, 29), S.WEEK),
        (date(2026, 11, 30), S.FINAL),
        (date(2027, 2, 21), S.WEEK),
        (date(2027, 2, 28), S.FINAL),
        (date(2028, 2, 22), S.WEEK),
        (date(2028, 2, 29), S.FINAL),
    ],
)
def test_due_stage(today, stage):
    assert due_stage(today) == stage


def test_target_month():
    assert target_month(date(2026, 11, 10)) == date(2026, 12, 1)
    assert target_month(date(2026, 12, 10)) == date(2027, 1, 1)


def _local(y, m, d, h=12, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=settings.COMMUNITY_TZ)


def _event(club, start, **kw):
    kw.setdefault("event_type", EventType.CLUB)
    kw.setdefault("status", EventStatus.ACTIVE)
    return Event.objects.create(title="e", club=club, start_datetime=start, **kw)


@pytest.mark.django_db
class TestUncoveredClubs:
    month = date(2026, 12, 1)

    def _uncovered(self):
        return set(uncovered_clubs(self.month))

    def test_covered_at_month_end(self):
        club = Club.objects.create(name="a")
        _event(club, _local(2026, 12, 31, 23, 30))
        assert club not in self._uncovered()

    def test_next_month_only_is_uncovered(self):
        club = Club.objects.create(name="a")
        _event(club, _local(2027, 1, 1, 0, 30))
        assert club in self._uncovered()

    @pytest.mark.parametrize(
        "kw",
        [
            {"status": EventStatus.DRAFT},
            {"status": EventStatus.CANCELLED},
            {"event_type": EventType.COMMUNITY},
        ],
    )
    def test_non_qualifying_is_uncovered(self, kw):
        club = Club.objects.create(name="a")
        _event(club, _local(2026, 12, 5), **kw)
        assert club in self._uncovered()

    def test_tbd_is_uncovered(self):
        club = Club.objects.create(name="a")
        _event(club, None)
        assert club in self._uncovered()

    def test_other_clubs_event_does_not_cover(self):
        a, b = Club.objects.create(name="a"), Club.objects.create(name="b")
        _event(a, _local(2026, 12, 5), status=EventStatus.DRAFT)
        _event(b, _local(2026, 12, 6))
        assert self._uncovered() == {a}

    def test_single_query(self, django_assert_num_queries):
        with django_assert_num_queries(1):
            list(uncovered_clubs(self.month))


@pytest.mark.django_db
def test_reminder_unique_per_club_month_stage():
    club = Club.objects.create(name="a")
    ClubEventReminder.objects.create(club=club, month=date(2026, 12, 1), stage=S.EARLY)
    with pytest.raises(IntegrityError), transaction.atomic():
        ClubEventReminder.objects.create(club=club, month=date(2026, 12, 1), stage=S.EARLY)
    ClubEventReminder.objects.create(club=club, month=date(2026, 12, 1), stage=S.WEEK)
