import asyncio
import json
import re
from datetime import timedelta

import pytest
from community import _events as community_events
from community._event_description_templates import (
    OFFICIAL_NON_WALK_TEMPLATE,
    OFFICIAL_WALK_TEMPLATE,
)
from community.models import Event, EventStatus, EventTag, EventType, PageVisibility
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.event_templates import template_slots
from mcp_gateway.server import pda_mcp

from tests._public_rsvp_helpers import make_non_member, make_tentative_member
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def _event(user, title, days=7, **fields):
    start = timezone.now() + timedelta(days=days)
    return Event.objects.create(title=title, created_by=user, start_datetime=start, **fields)


def _call(user, name, **arguments):
    token = _signed_in(user)
    try:
        return asyncio.run(pda_mcp.call_tool(name, arguments)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _error(user, name, **arguments) -> dict:
    with pytest.raises(ToolError) as exc_info:
        _call(user, name, **arguments)
    return json.loads(str(exc_info.value).split(": ", 1)[1])


def test_list_my_events_hosted_and_drafts_upcoming_first(test_user):
    other = make_non_member("+12025550199", "o@e.com")
    _event(test_user, "later", days=9)
    soon = _event(other, "soon", days=2)
    soon.co_hosts.add(test_user)
    draft = _event(test_user, "draft", days=5, status=EventStatus.DRAFT)
    _event(test_user, "past", days=-3)
    Event.objects.create(title="tbd", created_by=test_user, datetime_tbd=True)
    _event(test_user, "tbd dated", days=1, datetime_tbd=True)
    _event(other, "not mine")
    _event(other, "their draft", status=EventStatus.DRAFT)
    body = _call(test_user, "list_my_events")
    titles = [r["title"] for r in body["events"]]
    assert titles[:3] == ["soon", "draft", "later"] and set(titles[3:]) == {"tbd", "tbd dated"}
    assert body["next_offset"] is None
    assert body["events"][1]["status"] == "draft"
    assert body["events"][1]["url"].endswith(f"/events/{draft.slug}")
    with_past = _call(test_user, "list_my_events", include_past=True)["events"]
    assert [r["title"] for r in with_past][-1] == "past"


def test_list_my_events_serializes_only_hosted_rows(test_user, monkeypatch):
    other = make_non_member("+12025550199", "o@e.com")
    _event(test_user, "mine")
    _event(test_user, "past", days=-3)
    for i in range(5):
        _event(other, f"public {i}", visibility=PageVisibility.PUBLIC)
    serialized = []
    real = community_events._event_list_out
    monkeypatch.setattr(
        community_events,
        "_event_list_out",
        lambda e, *args: serialized.append(e.title) or real(e, *args),
    )
    assert [r["title"] for r in _call(test_user, "list_my_events")["events"]] == ["mine"]
    assert serialized == ["mine"]


def test_list_my_events_pages(test_user):
    for day in range(1, 6):
        _event(test_user, f"day {day}", days=day)
    first = _call(test_user, "list_my_events", limit=2)
    assert [r["title"] for r in first["events"]] == ["day 1", "day 2"]
    assert first["next_offset"] == 2
    last = _call(test_user, "list_my_events", limit=2, offset=4)
    assert ([r["title"] for r in last["events"]], last["next_offset"]) == (["day 5"], None)
    with pytest.raises(ToolError):
        _call(test_user, "list_my_events", limit=51)


def test_list_my_events_pages_tied_events_by_id(test_user):
    tied = [_event(test_user, f"tbd {i}", datetime_tbd=True) for i in range(5)]
    _event(test_user, "tbd draft", datetime_tbd=True, status=EventStatus.DRAFT)
    pages = [_call(test_user, "list_my_events", limit=2, offset=o)["events"] for o in (0, 2, 4)]
    ids = [r["id"] for page in pages for r in page]
    assert ids == sorted(ids) and len(set(ids)) == len(tied) + 1


def test_get_event_by_slug_or_id(test_user):
    event = _event(test_user, "picnic", location="prospect park")
    body = _call(test_user, "get_event", event=event.slug)
    assert (body["id"], body["location"]) == (str(event.id), "prospect park")
    assert _call(test_user, "get_event", event=str(event.id))["url"].endswith(event.slug)


def test_get_event_hides_someone_elses_draft(test_user):
    draft = _event(make_non_member("+12025550199", "o@e.com"), "x", status=EventStatus.DRAFT)
    assert _error(test_user, "get_event", event=draft.slug)["status"] == 403
    assert _call(test_user, "list_my_events")["events"] == []


def test_tentative_member_gets_the_views_visibility(test_user):
    tentative = make_tentative_member("+12025550177", "t@e.com")
    hidden = PageVisibility.MEMBERS_ONLY
    members_only = _event(test_user, "members", event_type=EventType.COMMUNITY, visibility=hidden)
    official = _event(test_user, "official", event_type=EventType.OFFICIAL, visibility=hidden)
    assert _error(tentative, "get_event", event=members_only.slug)["status"] == 404
    assert _call(tentative, "get_event", event=official.slug)["title"] == "official"


def test_list_event_tags(test_user):
    tag = EventTag.objects.create(name="walk", slug="walk")
    tags = _call(test_user, "list_event_tags")["result"]
    assert {"id": str(tag.id), "name": "walk", "slug": "walk"} in tags


def test_official_templates_with_slots(test_user):
    body = _call(test_user, "get_official_event_templates")
    walk = {"text": OFFICIAL_WALK_TEMPLATE, "slots": template_slots(OFFICIAL_WALK_TEMPLATE)}
    assert body["official_walk"] == walk and len(walk["slots"]) == 9
    assert body["official_non_walk"]["slots"] == ["WHAT WE'RE ORDERING, PER PERSON"]


@pytest.mark.parametrize("template", [OFFICIAL_WALK_TEMPLATE, OFFICIAL_NON_WALK_TEMPLATE])
def test_template_slots_cover_every_placeholder(template):
    bracketed = set(re.findall(r"\[([^\]]*)\]", template))
    assert bracketed and set(template_slots(template)) == bracketed


def test_template_slots_dedupes_and_skips_lowercase():
    assert template_slots("see [link] and [A] [A]") == ["A"]
