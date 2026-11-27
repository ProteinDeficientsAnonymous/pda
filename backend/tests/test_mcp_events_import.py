import json
from unittest.mock import patch

import pytest
from community.models import Event, EventRSVP, EventStatus, EventType
from community.validation import Code
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error
from tests._users import grant

pytestmark = pytest.mark.django_db
PAST = {"title": "summer potluck 2023", "start_datetime": "2023-07-04T18:00"}


@pytest.fixture
def events_admin(test_user):
    grant(test_user, PermissionKey.MANAGE_EVENTS)
    return test_user


@pytest.mark.parametrize(
    ("flag", "field"), [("legacy", "is_legacy"), ("partiful_import", "is_partiful_import")]
)
def test_backfills_past_event_off_the_calendar(events_admin, flag, field):
    with patch("community.events.crud.broadcast_event_created") as broadcast:
        summary = run_tool(events_admin, "create_event", fields=PAST, **{flag: True})
    event = Event.objects.get(pk=summary["id"])
    assert (event.status, getattr(event, field)) == (EventStatus.ACTIVE, True)
    assert summary[field] is True
    broadcast.assert_not_called()


def test_backfill_skips_host_auto_rsvp(events_admin):
    grant(events_admin, PermissionKey.TAG_OFFICIAL_EVENT)
    fields = {**PAST, "event_type": EventType.OFFICIAL, "event_format": "walk"}
    summary = run_tool(events_admin, "create_event", fields=fields, legacy=True)
    assert not EventRSVP.objects.filter(event_id=summary["id"]).exists()


def test_manage_users_can_backfill(test_user):
    grant(test_user, PermissionKey.MANAGE_USERS)
    summary = run_tool(test_user, "create_event", fields=PAST, legacy=True)
    assert Event.objects.get(pk=summary["id"]).is_legacy


def test_backfill_needs_permission(test_user):
    error = json.loads(tool_error(test_user, "create_event", fields=PAST, legacy=True))
    assert error["status"] == 403
    assert not Event.objects.exists()


def test_past_date_still_refused_without_flag(events_admin):
    error = json.loads(tool_error(events_admin, "create_event", fields=PAST))
    assert error["detail"][0]["code"] == Code.Event.START_DATETIME_MUST_BE_FUTURE
    assert not Event.objects.exists()
