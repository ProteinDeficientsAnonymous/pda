from datetime import timedelta

import pytest
from community.models import AttendanceStatus, EventStatus, EventType, RSVPStatus
from django.utils import timezone

from tests._events import make_event, make_rsvp
from tests._mcp_members_helpers import make_member
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._public_rsvp_helpers import make_public_rsvper

pytestmark = pytest.mark.django_db

ATTENDED = AttendanceStatus.ATTENDED


def _event(days_ago: float, event_type: str = EventType.OFFICIAL, **fields):
    return make_event(
        start_datetime=timezone.now() - timedelta(days=days_ago), event_type=event_type, **fields
    )


def test_hidden_and_forbidden_without_permission(test_user):
    assert "event_trends" not in tool_names(test_user)
    assert "permission" in tool_error(test_user, "event_trends")


@pytest.mark.parametrize("fixture", ["manage_events_user", "manage_users_user"])
def test_either_permission_may_use_it(request, fixture):
    assert "event_trends" in tool_names(request.getfixturevalue(fixture))


def test_counts_per_type_with_unmarked_events_and_public_rsvps(manage_events_user):
    a, b, public = make_member(), make_member(), make_public_rsvper("+12025559001", "n@e.com")
    official = _event(10)
    unmarked_club = _event(12, EventType.CLUB)
    community = _event(11, EventType.COMMUNITY)
    for user in (a, b, public):
        make_rsvp(official, user, attendance=ATTENDED)
    make_rsvp(_event(12), make_member(), has_plus_one=True, plus_one_attendance=ATTENDED)
    make_rsvp(_event(0.01), a, attendance=ATTENDED)
    make_rsvp(unmarked_club, a)
    make_rsvp(community, a, attendance=ATTENDED)
    make_rsvp(_event(5, status=EventStatus.CANCELLED), a, attendance=ATTENDED)
    make_rsvp(_event(5, status=EventStatus.DRAFT), a, attendance=ATTENDED)
    make_rsvp(_event(400), a, attendance=ATTENDED)

    total = run_tool(manage_events_user, "event_trends", days=60, bucket="month")["total"]

    assert total["official"] == {
        "events": 2,
        "events_without_attendance_marked": 0,
        "attended": 4,
        "unique_attended_members": 2,
        "avg_attended_per_marked_event": 2.0,
        "going_headcount": 5,
    }
    assert total["club"]["events"] == 1
    assert total["club"]["events_without_attendance_marked"] == 1
    assert total["club"]["attended"] == 0
    assert total["club"]["going_headcount"] == 1
    assert total["club"]["avg_attended_per_marked_event"] is None
    assert (total["community"]["events"], total["community"]["attended"]) == (1, 1)


def test_buckets_events_by_month_and_week(manage_users_user):
    first, second = _event(40), _event(2)
    make_rsvp(first, make_member(), attendance=ATTENDED)
    make_rsvp(second, make_member(), status=RSVPStatus.CANT_GO)

    months = run_tool(manage_users_user, "event_trends", days=60)["buckets"]
    weeks = run_tool(manage_users_user, "event_trends", days=60, bucket="week")["buckets"]

    assert sum(b["official"]["events"] for b in months) == 2
    assert [b["official"]["events"] for b in weeks] == [1, 1]
    assert [b["official"]["going_headcount"] for b in weeks] == [1, 0]
    assert [b["official"]["attended"] for b in weeks] == [1, 0]
    assert weeks[0]["bucket"] < weeks[1]["bucket"]


def test_empty_window_has_zeroed_shape(manage_events_user):
    body = run_tool(manage_events_user, "event_trends", days=7)

    assert body["buckets"] == []
    assert set(body["total"]) == {"official", "club", "community"}
