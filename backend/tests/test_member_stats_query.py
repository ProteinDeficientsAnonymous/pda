from datetime import timedelta
from itertools import product

import pytest
from community._attendance_analytics import (
    EMPTY_MEMBER_STATS,
    compute_member_stats,
    member_stats_by_user,
    user_rsvps_for_attendance,
)
from community.models import AttendanceStatus, Event, EventRSVP, EventStatus, EventType, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from users.models import User

from tests._auth import auth_headers_for
from tests._users import make_user
from tests.test_member_attendance_analytics import MEMBERS_URL, events_admin  # noqa: F401

_seq = {"n": 0}


def _members(count: int) -> list[User]:
    host = make_user()
    events = [
        Event.objects.create(
            title="e",
            start_datetime=None if days is None else timezone.now() - timedelta(days=days),
            event_type=event_type,
            status=status,
            created_by=host,
        )
        for event_type, days, status in product(
            [EventType.CLUB, EventType.OFFICIAL, EventType.COMMUNITY],
            [5, 400, None],
            [EventStatus.ACTIVE, EventStatus.CANCELLED],
        )
    ]
    attendances = [AttendanceStatus.ATTENDED, AttendanceStatus.DIDNT_GO, AttendanceStatus.UNKNOWN]
    members = []
    for _ in range(count):
        _seq["n"] += 1
        user = make_user(is_member=True)
        for i, event in enumerate(events[_seq["n"] % 4 :]):
            EventRSVP.objects.create(
                event=event,
                user=user,
                status=RSVPStatus.ATTENDING,
                attendance=attendances[(i + _seq["n"]) % 3],
                cancelled_at=timezone.now() if i % 5 == 0 else None,
            )
        members.append(user)
    return members


@pytest.mark.django_db
class TestMemberStatsQuery:
    def test_matches_python_stats(self):
        members = [*_members(4), make_user(is_member=True)]
        now = timezone.now()
        stats = member_stats_by_user(User.objects.filter(is_member=True), now)
        for user in members:
            expected = compute_member_stats(user_rsvps_for_attendance(user), now)
            assert stats.get(user.pk, EMPTY_MEMBER_STATS) == expected

    def test_endpoint_is_constant(self, api_client, events_admin):  # noqa: F811
        def count() -> int:
            with CaptureQueriesContext(connection) as ctx:
                response = api_client.get(MEMBERS_URL, **auth_headers_for(events_admin))
            assert response.status_code == 200
            return len(ctx.captured_queries)

        _members(2)
        small = count()
        _members(6)
        assert count() == small
