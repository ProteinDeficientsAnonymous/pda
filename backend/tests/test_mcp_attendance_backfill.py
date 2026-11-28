from datetime import timedelta

import pytest
from community.models import AttendanceStatus, Event, EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from users.permissions import PermissionKey

from tests._events import make_rsvp
from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOL = "mark_attended"
pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(db):
    return make_user(PermissionKey.MANAGE_USERS, first_name="Admin")


@pytest.fixture
def members(db):
    return [make_user(first_name="Robin"), make_user(first_name="Sam")]


@pytest.fixture
def past_event(admin):
    start = timezone.now() - timedelta(days=400)
    return Event.objects.create(title="old potluck", start_datetime=start, created_by=admin)


def _ids(members) -> list[str]:
    return [str(m.pk) for m in members]


def _confirm(user, **args) -> dict:
    preview = run_tool(user, TOOL, **args)
    return run_tool(user, TOOL, **args, confirm_token=preview["confirm_token"])


def _attended(event) -> set:
    rows = EventRSVP.objects.filter(
        event=event, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.ATTENDED
    )
    return set(rows.values_list("user_id", flat=True))


def test_preview_shows_current_rsvps_and_changes_nothing(admin, members, past_event):
    make_rsvp(past_event, members[0], status=RSVPStatus.CANT_GO)
    preview = run_tool(admin, TOOL, member_ids=_ids(members), event_id=str(past_event.pk))
    assert [m["current_rsvp"] for m in preview["members"]] == [RSVPStatus.CANT_GO, None]
    assert preview["event"]["title"] == "old potluck"
    assert not _attended(past_event)


def test_marks_members_without_rsvps_on_a_past_event(admin, members, past_event):
    make_rsvp(past_event, members[0], status=RSVPStatus.CANT_GO)
    result = _confirm(admin, member_ids=_ids(members), event_id=str(past_event.pk))
    assert (result["created_count"], result["updated_count"]) == (1, 1)
    assert _attended(past_event) == {m.pk for m in members}


def test_creates_legacy_event_and_marks_members(admin, members):
    new = {"title": "summer walk 2023", "event_date": "2023-07-04", "event_type": "official"}
    result = _confirm(admin, member_ids=_ids(members), new_legacy_event=new)
    event = Event.objects.get(pk=result["event_id"])
    assert (event.is_legacy, event.event_type) == (True, EventType.OFFICIAL)
    assert _attended(event) == {m.pk for m in members}


def test_changed_rsvp_invalidates_token(admin, members, past_event):
    args = {"member_ids": _ids(members), "event_id": str(past_event.pk)}
    preview = run_tool(admin, TOOL, **args)
    make_rsvp(past_event, members[1])
    tool_error(admin, TOOL, **args, confirm_token=preview["confirm_token"])
    assert not _attended(past_event)


@pytest.mark.parametrize("event", [None, "both"])
def test_needs_exactly_one_event(admin, members, past_event, event):
    new = {"title": "x", "event_date": "2023-07-04"}
    args = {"event_id": str(past_event.pk), "new_legacy_event": new} if event else {}
    error = tool_error(admin, TOOL, member_ids=_ids(members), **args)
    assert "exactly one of event_id or new_legacy_event" in error


def test_hidden_without_manage_users(members):
    assert TOOL not in tool_names(members[0])
