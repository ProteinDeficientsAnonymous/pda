from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from community.models import Club, Event, EventStatus, EventType
from django.conf import settings
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp_gateway.server import BASE_URL, pda_mcp

from tests._mcp_tool_helpers import signed_in

pytestmark = pytest.mark.django_db


def _text(user, **arguments) -> str:
    token = signed_in(user)
    try:
        result = async_to_sync(pda_mcp.call_tool)("upcoming_events", arguments)
        assert result.structured_content is not None
        return result.structured_content["result"]
    finally:
        auth_context_var.reset(token)


def _event(user, title, days, **fields):
    fields.setdefault("event_type", EventType.OFFICIAL)
    start = timezone.now() + timedelta(days=days)
    return Event.objects.create(title=title, created_by=user, start_datetime=start, **fields)


def _md(event) -> str:
    local = event.start_datetime.astimezone(settings.COMMUNITY_TZ)
    return f"{local.month}/{local.day}"


def test_upcoming_events_groups_by_club_in_date_order(test_user):
    outdoor = Club.objects.create(name="Outdoor Adventures")
    club = {"event_type": EventType.CLUB, "club": outdoor}
    skate = _event(test_user, "Ice skating", 2, location="Prospect Park", **club)
    potluck = _event(test_user, "Potluck", 3)
    hike = _event(test_user, "Hike", 5, **club)
    assert _text(test_user) == (
        "Outdoor Adventures\n"
        f"{_md(skate)} Ice skating @ Prospect Park\n{BASE_URL}/events/{skate.slug}\n"
        f"{_md(hike)} Hike\n{BASE_URL}/events/{hike.slug}\n"
        "\n"
        f"Official\n{_md(potluck)} Potluck\n{BASE_URL}/events/{potluck.slug}"
    )


def test_upcoming_events_skips_community_past_underway_tbd_far_and_drafts(test_user):
    _event(test_user, "community", 1, event_type=EventType.COMMUNITY)
    _event(test_user, "past", -3)
    _event(test_user, "underway", -1, end_datetime=timezone.now() + timedelta(days=1))
    _event(test_user, "far", 30)
    _event(test_user, "draft", 1, status=EventStatus.DRAFT)
    Event.objects.create(
        title="tbd", created_by=test_user, datetime_tbd=True, event_type=EventType.OFFICIAL
    )
    _event(test_user, "tbd dated", 2, datetime_tbd=True)
    assert _text(test_user) == "no upcoming events in the next 14 days"
    assert "far" in _text(test_user, days=31)
