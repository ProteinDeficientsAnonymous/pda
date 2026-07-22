"""Tests for anchor + milestone due-date math (community/_attendance_clock.py)."""

from datetime import UTC, date, datetime

import pytest
from community._attendance_clock import compute_anchor, latest_due_milestone, milestone_due_date
from community.models import AttendanceMilestone, AttendanceStatus, Event, EventRSVP, EventType
from users.models import User


def _make_user(date_joined: date, **extra) -> User:
    user = User.objects.create_user(
        phone_number=extra.pop("phone_number", "+12025550100"),
        password="testpass123",
        first_name="Test",
        is_member=True,
        **extra,
    )
    User.objects.filter(pk=user.pk).update(
        date_joined=datetime.combine(date_joined, datetime.min.time(), tzinfo=UTC)
    )
    user.refresh_from_db()
    return user


def _make_event(*, event_type: str, start: date) -> Event:
    return Event.objects.create(
        title="test event",
        event_type=event_type,
        start_datetime=datetime.combine(start, datetime.min.time(), tzinfo=UTC),
    )


def _attend(user: User, event: Event) -> None:
    EventRSVP.objects.create(
        user=user,
        event=event,
        status="attending",
        attendance=AttendanceStatus.ATTENDED,
    )


@pytest.mark.django_db
class TestComputeAnchor:
    def test_floor_wins_when_nothing_else_qualifies(self):
        user = _make_user(date_joined=date(2020, 1, 1))
        anchor = compute_anchor(user, today=date(2026, 8, 15))
        assert anchor == date(2026, 8, 1)

    def test_date_joined_wins_when_after_floor(self):
        user = _make_user(date_joined=date(2026, 9, 1))
        anchor = compute_anchor(user, today=date(2026, 12, 1))
        assert anchor == date(2026, 9, 1)

    def test_qualifying_attendance_advances_anchor(self):
        user = _make_user(date_joined=date(2020, 1, 1))
        event = _make_event(event_type=EventType.CLUB, start=date(2026, 9, 10))
        _attend(user, event)
        anchor = compute_anchor(user, today=date(2026, 12, 1))
        assert anchor == date(2026, 9, 10)

    def test_community_event_attendance_does_not_advance_anchor(self):
        user = _make_user(date_joined=date(2020, 1, 1))
        event = _make_event(event_type=EventType.COMMUNITY, start=date(2026, 9, 10))
        _attend(user, event)
        anchor = compute_anchor(user, today=date(2026, 12, 1))
        assert anchor == date(2026, 8, 1)

    def test_uses_latest_qualifying_attendance(self):
        user = _make_user(date_joined=date(2020, 1, 1))
        older = _make_event(event_type=EventType.OFFICIAL, start=date(2026, 9, 1))
        newer = _make_event(event_type=EventType.CLUB, start=date(2026, 10, 5))
        _attend(user, older)
        _attend(user, newer)
        anchor = compute_anchor(user, today=date(2026, 12, 1))
        assert anchor == date(2026, 10, 5)

    def test_non_attended_rsvp_does_not_count(self):
        user = _make_user(date_joined=date(2020, 1, 1))
        event = _make_event(event_type=EventType.CLUB, start=date(2026, 9, 10))
        EventRSVP.objects.create(
            user=user, event=event, status="attending", attendance=AttendanceStatus.NO_SHOW
        )
        anchor = compute_anchor(user, today=date(2026, 12, 1))
        assert anchor == date(2026, 8, 1)


class TestMilestoneDueDate:
    def test_m10_is_10_months_after_anchor(self):
        assert milestone_due_date(date(2026, 8, 1), AttendanceMilestone.M10) == date(2027, 6, 1)

    def test_m11_is_11_months_after_anchor(self):
        assert milestone_due_date(date(2026, 8, 1), AttendanceMilestone.M11) == date(2027, 7, 1)

    def test_m11_5_is_11_months_15_days_after_anchor(self):
        assert milestone_due_date(date(2026, 8, 1), AttendanceMilestone.M11_5) == date(2027, 7, 16)

    def test_m12_is_12_months_after_anchor(self):
        assert milestone_due_date(date(2026, 8, 1), AttendanceMilestone.M12) == date(2027, 8, 1)


class TestLatestDueMilestone:
    def test_none_due_before_10_months(self):
        anchor = date(2026, 8, 1)
        assert latest_due_milestone(anchor, today=date(2027, 5, 31)) is None

    def test_m10_due_at_boundary(self):
        anchor = date(2026, 8, 1)
        due = latest_due_milestone(anchor, today=date(2027, 6, 1))
        assert due.milestone == AttendanceMilestone.M10

    def test_m10_due_day_before_m11(self):
        anchor = date(2026, 8, 1)
        due = latest_due_milestone(anchor, today=date(2027, 6, 30))
        assert due.milestone == AttendanceMilestone.M10

    def test_returns_latest_when_multiple_due(self):
        """A user who crossed 10mo and 11mo since the last run gets only 11mo."""
        anchor = date(2026, 8, 1)
        due = latest_due_milestone(anchor, today=date(2027, 7, 1))
        assert due.milestone == AttendanceMilestone.M11

    def test_returns_m12_when_all_due(self):
        anchor = date(2026, 8, 1)
        due = latest_due_milestone(anchor, today=date(2028, 1, 1))
        assert due.milestone == AttendanceMilestone.M12

    def test_anchor_date_attached_to_due_result(self):
        anchor = date(2026, 8, 1)
        due = latest_due_milestone(anchor, today=date(2027, 6, 1))
        assert due.anchor_date == anchor
