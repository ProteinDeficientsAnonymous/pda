from datetime import timedelta
from uuid import uuid4

import pytest
from community.models import AttendanceStatus, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from mcp_gateway.tools.members_rsvps import _page

from tests._events import make_event, make_rsvp
from tests._mcp_members_helpers import make_member
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._public_rsvp_helpers import make_non_member

pytestmark = pytest.mark.django_db


def _event(days_ago: float, **fields):
    return make_event(start_datetime=timezone.now() - timedelta(days=days_ago), **fields)


def test_hidden_and_forbidden_without_manage_users(test_user):
    assert "member_rsvps" not in tool_names(test_user)
    assert "permission" in tool_error(test_user, "member_rsvps", member=str(test_user.id))


def test_unknown_or_non_member_id_is_an_error(manage_users_user):
    outsider = make_non_member("+12025559001", "n@e.com")
    for member in (uuid4(), outsider.id):
        assert tool_error(manage_users_user, "member_rsvps", member=str(member)) == (
            "no member with that id"
        )


def test_lists_every_rsvp_latest_first_with_qualifying_flag(manage_users_user):
    member = make_member(last_name="Lee")
    official = _event(10, title="Walk", event_type=EventType.OFFICIAL)
    community = _event(20, event_type=EventType.COMMUNITY)
    cancelled = _event(30, event_type=EventType.OFFICIAL, status=EventStatus.CANCELLED)
    undated = make_event(start_datetime=None, datetime_tbd=True)
    make_rsvp(official, member, attendance=AttendanceStatus.ATTENDED)
    make_rsvp(community, member, attendance=AttendanceStatus.ATTENDED)
    make_rsvp(cancelled, member, attendance=AttendanceStatus.ATTENDED)
    make_rsvp(undated, member, status=RSVPStatus.CANT_GO)
    make_rsvp(official, make_member())

    body = run_tool(manage_users_user, "member_rsvps", member=str(member.id))

    assert body["member"] == {"id": str(member.id), "name": "M Lee"}
    assert body["total"] == 4
    assert [(r["event_id"], r["qualifying"]) for r in body["rsvps"]] == [
        (str(official.id), True),
        (str(community.id), False),
        (str(cancelled.id), False),
        (str(undated.id), False),
    ]
    first = body["rsvps"][0]
    assert first["event_title"] == "Walk"
    assert first["status"] == RSVPStatus.ATTENDING
    assert first["attendance"] == AttendanceStatus.ATTENDED
    assert body["rsvps"][3]["event_start_datetime"] is None


def test_since_days_and_paging(manage_users_user):
    member = make_member()
    for days_ago in (5, 15, 25, 400):
        make_rsvp(_event(days_ago), member)
    make_rsvp(make_event(start_datetime=None, datetime_tbd=True), member)

    recent = run_tool(manage_users_user, "member_rsvps", member=str(member.id), since_days=30)
    assert recent["total"] == 3

    page = run_tool(manage_users_user, "member_rsvps", member=str(member.id), limit=2, offset=4)
    assert (len(page["rsvps"]), page["next_offset"]) == (1, None)
    first = run_tool(manage_users_user, "member_rsvps", member=str(member.id), limit=2)
    assert first["next_offset"] == 2


def test_one_page_is_three_queries(django_assert_num_queries):
    member = make_member()
    for days_ago in (1, 2, 3):
        make_rsvp(_event(days_ago), member)
    with django_assert_num_queries(3):
        assert len(_page(member.id, None, limit=2, offset=0)["rsvps"]) == 2
