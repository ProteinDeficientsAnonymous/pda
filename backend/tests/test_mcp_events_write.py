import asyncio
import json
from functools import partial
from unittest.mock import patch

import pytest
from audit.models import AuditLogEntry
from community._validation import Code
from community.models import Event, EventTag
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from users.models import User

from tests.test_geocode import _FakeResp
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
WALK = {"title": "prospect park walk", "start_datetime": "2099-11-07T11:00:00-05:00"}


def _run(user, tool, **arguments):
    reset = _signed_in(user)
    try:
        return asyncio.run(pda_mcp.call_tool(tool, arguments)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(reset)


def _error(user, tool, **arguments) -> str:
    with pytest.raises(ToolError) as exc_info:
        _run(user, tool, **arguments)
    return str(exc_info.value).removeprefix(f"Error executing tool {tool}: ")


def test_creates_draft_as_member_via_mcp(test_user):
    EventTag.objects.create(name="walk")
    fields = {**WALK, "price": "$15", "latitude": 40.67, "longitude": -73.97, "tags": ["Walk"]}
    summary = _run(test_user, "create_event", fields=fields)
    event = Event.objects.get(pk=summary["id"])
    assert (event.status, event.created_by, event.price) == ("draft", test_user, "$15")
    assert (summary["start_datetime"], summary["tags"]) == ("2099-11-07T11:00:00-05:00", ["walk"])
    assert summary["url"].endswith(f"/events/{event.slug or event.id}")
    entry = AuditLogEntry.objects.get(target_id=summary["id"])
    assert (entry.action, entry.actor) == ("event_created_draft", test_user)
    assert entry.details["via"] == "mcp"


@pytest.mark.parametrize(("is_member", "event_type"), [(True, "official"), (False, "community")])
def test_view_refuses_official_without_permission_and_tentative(test_user, is_member, event_type):
    User.objects.filter(pk=test_user.pk).update(is_member=is_member)
    error = _error(test_user, "create_event", fields={**WALK, "event_type": event_type})
    assert json.loads(error)["status"] == 403


def test_unknown_tag_lists_valid_ones(test_user):
    EventTag.objects.create(name="walk")
    error = _error(test_user, "create_event", fields={**WALK, "tags": ["hike"]})
    assert error == "unknown tags: hike. valid tags: walk"


def test_rate_limit_shared_with_website(test_user, api_client, auth_headers):
    post = partial(api_client.post, content_type="application/json", **auth_headers)
    assert all(post("/api/community/events/", WALK).status_code == 201 for _ in range(10))
    error = json.loads(_error(test_user, "create_event", fields=WALK))
    assert (error["status"], error["detail"][0]["code"]) == (429, Code.Rate.LIMITED)


def test_find_location_returns_candidates(test_user):
    props = {"name": "grand army plaza", "street": "flatbush ave", "city": "New York"}
    feature = {"geometry": {"coordinates": [-73.97, 40.67]}, "properties": props}
    with patch("community._geocode.httpx.get", return_value=_FakeResp({"features": [feature]})):
        result = _run(test_user, "find_location", query="grand army plaza")
    place = {"name": "grand army plaza", "address": "flatbush ave, New York"}
    assert result == {"result": [{**place, "lat": 40.67, "lon": -73.97}]}
