from datetime import timedelta

import pytest
from community.attendance.no_shows import members_with_repeated_no_shows
from community.models import AttendanceStatus, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from users.models import MembershipStatus

from tests._events import make_event, make_rsvp
from tests._mcp_members_helpers import make_member
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names

pytestmark = pytest.mark.django_db

DIDNT_GO = AttendanceStatus.DIDNT_GO


def _event(days_ago: float, event_type=EventType.OFFICIAL, **fields):
    start = timezone.now() - timedelta(days=days_ago)
    return make_event(start_datetime=start, event_type=event_type, **fields)


def _no_shows(member, *days_ago: float, event_type=EventType.OFFICIAL, **fields):
    for days in days_ago:
        make_rsvp(_event(days, event_type, **fields), member, attendance=DIDNT_GO)


def _flagged(user) -> dict[str, dict]:
    body = run_tool(user, "repeated_no_shows")
    assert body["total"] == len(body["members"])
    return {row["user_id"]: row for row in body["members"]}


def test_hidden_and_refused_without_manage_events(test_user, manage_users_user):
    for user in (test_user, manage_users_user):
        assert "repeated_no_shows" not in tool_names(user)
        assert "permission" in tool_error(user, "repeated_no_shows")


def test_three_qualifying_no_shows_flag_a_member(manage_events_user):
    flagged = make_member(last_name="Three")
    _no_shows(flagged, 10, 20)
    _no_shows(flagged, 30, event_type=EventType.CLUB)
    two = make_member()
    _no_shows(two, 10, 20)
    community = make_member()
    _no_shows(community, 10, 20)
    _no_shows(community, 30, event_type=EventType.COMMUNITY)
    cancelled = make_member()
    _no_shows(cancelled, 10, 20)
    _no_shows(cancelled, 30, status=EventStatus.CANCELLED)
    archived = make_member(membership_status=MembershipStatus.ARCHIVED, archived_at=timezone.now())
    _no_shows(archived, 10, 20, 30)

    rows = _flagged(manage_events_user)

    assert list(rows) == [str(flagged.id)]
    assert rows[str(flagged.id)]["full_name"] == "M Three"
    assert rows[str(flagged.id)]["no_show_count"] == 3


def test_last_no_show_and_recent_rsvps_newest_first_capped(manage_events_user):
    member = make_member()
    _no_shows(member, 40, 50)
    _no_shows(member, 5, title="latest miss")
    for days_ago in (10, 20, 30):
        make_rsvp(
            _event(days_ago, title=f"went {days_ago}"), member, attendance=AttendanceStatus.ATTENDED
        )
    make_rsvp(_event(15, EventType.COMMUNITY), member, attendance=DIDNT_GO)
    make_rsvp(_event(-3, title="upcoming"), member)
    make_rsvp(_event(25, title="cant go"), member, status=RSVPStatus.CANT_GO)

    row = _flagged(manage_events_user)[str(member.id)]

    assert row["last_no_show"]["title"] == "latest miss"
    history = [(r["title"], r["status"], r["attendance"]) for r in row["recent_rsvps"]]
    assert history == [
        ("latest miss", RSVPStatus.ATTENDING, DIDNT_GO),
        ("went 10", RSVPStatus.ATTENDING, AttendanceStatus.ATTENDED),
        ("went 20", RSVPStatus.ATTENDING, AttendanceStatus.ATTENDED),
        ("cant go", RSVPStatus.CANT_GO, AttendanceStatus.UNKNOWN),
        ("went 30", RSVPStatus.ATTENDING, AttendanceStatus.ATTENDED),
    ]


def test_most_no_shows_first_in_two_queries(django_assert_num_queries):
    three, four = make_member(), make_member()
    _no_shows(three, 1, 2, 3)
    _no_shows(four, 4, 5, 6, 7)

    with django_assert_num_queries(2):
        rows = members_with_repeated_no_shows()

    assert [(r.user_id, r.no_show_count) for r in rows] == [(str(four.id), 4), (str(three.id), 3)]
    assert all(len(r.recent_rsvps) == r.no_show_count for r in rows)
