import asyncio
import json
import logging
import sys
from typing import Any

import pytest
from audit.models import AuditLogEntry
from community._event_description_templates import get_event_description_templates as templates
from community._event_schemas import EventIn
from community._events import create_event
from community._validation import Code, raise_validation
from community.models import Event
from config.audit import AuditTarget, audit_log, is_request_via_mcp
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway import tools
from mcp_gateway.server import TOOL_PERMISSIONS, current_user, pda_mcp, pda_tool
from mcp_gateway.view_calls import call_view
from ninja.responses import Status

from tests.test_mcp_flow import connect, mcp_client, rpc

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
DRAFT = EventIn(title="picnic", status="draft")


def _call(view, user, *args, **kwargs):
    return asyncio.run(call_view(view, user, *args, **kwargs))


def _tool_error(view, user, *args) -> dict:
    with pytest.raises(ToolError) as exc_info:
        _call(view, user, *args)
    return json.loads(str(exc_info.value))


def test_unwraps_status_models_and_lists(test_user):
    body = _call(templates, test_user)
    assert set(body) == {"official_walk", "official_non_walk"}
    assert _call(lambda r: Status(200, [templates(r).value]), test_user) == [body]


def test_runs_as_member_marked_via_mcp(test_user):
    def view(request, event_id, *, flag):
        return [request.auth == request.user == test_user, is_request_via_mcp(request), flag]

    assert _call(view, test_user, "abc", flag="x") == [True, True, "x"]


def test_validation_exception_becomes_tool_error(test_user):
    payload = EventIn(title="x", status="cancelled", datetime_tbd=True)
    assert _tool_error(create_event, test_user, payload) == {
        "status": 400,
        "detail": [{"code": Code.Event.INVALID_CREATE_STATUS, "field": "status"}],
    }


def test_audit_marked_via_mcp_and_rate_limit_kept(test_user):
    event = _call(create_event, test_user, DRAFT)
    entry = AuditLogEntry.objects.get(target_id=event["id"])
    assert entry.actor == test_user
    assert entry.details == {**entry.details, "title": "picnic", "via": "mcp"}
    for _ in range(9):
        _call(create_event, test_user, DRAFT)
    error = _tool_error(create_event, test_user, DRAFT)
    assert (error["status"], error["detail"][0]["code"]) == (429, Code.Rate.LIMITED)


def test_failed_view_rolls_back(test_user):
    def view(request):
        event = Event.objects.create(title="half", created_by=request.auth)
        audit_log(logging.INFO, "event_created", request, AuditTarget(id=str(event.id)))
        raise_validation(Code.Event.END_BEFORE_START, field="end_datetime")

    assert _tool_error(view, test_user)["status"] == 422
    assert not Event.objects.filter(title="half").exists()
    assert not AuditLogEntry.objects.filter(action="event_created").exists()


@pytest.fixture
def meta_tool():
    @pda_tool()
    async def echo_meta() -> dict[str, Any]:
        return await call_view(lambda request: dict(request.META), await current_user())

    yield "echo_meta"
    pda_mcp.remove_tool("echo_meta")
    TOOL_PERMISSIONS.pop("echo_meta")


def test_copies_client_meta_from_mcp_http_request(test_user, meta_tool):
    async def flow():
        async with mcp_client() as client:
            token = await connect(client, test_user)
            client.headers["X-Forwarded-For"] = "203.0.113.9"
            return (await rpc(client, token, "tools/call", name=meta_tool, arguments={})).json()

    meta = asyncio.run(flow())["result"]["structuredContent"]
    assert (meta["REMOTE_ADDR"], meta["HTTP_X_FORWARDED_FOR"]) == ("127.0.0.1", "203.0.113.9")
    assert "HTTP_AUTHORIZATION" not in meta


def test_load_tools_imports_every_module(tmp_path, monkeypatch):
    source = "from mcp_gateway.server import pda_tool\n\n@pda_tool()\ndef fake_tool() -> str: ..."
    (tmp_path / "fake_tool.py").write_text(source)
    monkeypatch.setattr(tools, "__path__", [*tools.__path__, str(tmp_path)])
    tools.load_tools()
    assert TOOL_PERMISSIONS.pop("fake_tool") == ()
    pda_mcp.remove_tool("fake_tool")
    sys.modules.pop("mcp_gateway.tools.fake_tool")
