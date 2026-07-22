"""Tests for the AttendanceReminder model's uniqueness constraint."""

from datetime import date

import pytest
from community.models import AttendanceMilestone, AttendanceReminder
from django.db import IntegrityError
from users.models import User


@pytest.fixture
def member(db) -> User:
    return User.objects.create_user(
        phone_number="+12025550199",
        password="testpass123",
        first_name="Test",
        is_member=True,
    )


@pytest.mark.django_db
class TestAttendanceReminderUniqueness:
    def test_duplicate_user_milestone_anchor_rejected(self, member):
        AttendanceReminder.objects.create(
            user=member, milestone=AttendanceMilestone.M10, anchor_date=date(2026, 8, 1)
        )
        with pytest.raises(IntegrityError):
            AttendanceReminder.objects.create(
                user=member, milestone=AttendanceMilestone.M10, anchor_date=date(2026, 8, 1)
            )

    def test_different_anchor_date_allowed(self, member):
        AttendanceReminder.objects.create(
            user=member, milestone=AttendanceMilestone.M10, anchor_date=date(2026, 8, 1)
        )
        AttendanceReminder.objects.create(
            user=member, milestone=AttendanceMilestone.M10, anchor_date=date(2026, 9, 1)
        )
        assert AttendanceReminder.objects.filter(user=member).count() == 2

    def test_different_milestone_same_anchor_allowed(self, member):
        AttendanceReminder.objects.create(
            user=member, milestone=AttendanceMilestone.M10, anchor_date=date(2026, 8, 1)
        )
        AttendanceReminder.objects.create(
            user=member, milestone=AttendanceMilestone.M11, anchor_date=date(2026, 8, 1)
        )
        assert AttendanceReminder.objects.filter(user=member).count() == 2
