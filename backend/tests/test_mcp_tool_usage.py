import logging

import pytest
from audit.models import AuditLogEntry
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import TOOL_PERMISSIONS, pda_mcp, pda_tool
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error

pytestmark = pytest.mark.django_db


@pytest.fixture
def broken_tool():
    @pda_tool()
    async def broken() -> dict:
        raise ToolError("nope")

    yield "broken"
    pda_mcp.remove_tool("broken")
    TOOL_PERMISSIONS.pop("broken")


@pytest.fixture
def admin_only_tool():
    @pda_tool(PermissionKey.MANAGE_USERS)
    async def admin_only() -> dict:
        return {}

    yield "admin_only"
    pda_mcp.remove_tool("admin_only")
    TOOL_PERMISSIONS.pop("admin_only")


def test_successful_call_is_recorded(manage_users_user):
    run_tool(manage_users_user, "whoami")
    entry = AuditLogEntry.objects.get(action="mcp_tool_called")
    assert entry.actor == manage_users_user
    assert entry.level == logging.INFO
    assert entry.details["tool"] == "whoami"
    assert entry.details["ok"] is True
    assert entry.details["duration_ms"] >= 0


def test_failed_call_is_recorded_as_a_warning(test_user, broken_tool):
    tool_error(test_user, broken_tool)
    entry = AuditLogEntry.objects.get(action="mcp_tool_called")
    assert entry.level == logging.WARNING
    assert entry.details["tool"] == broken_tool
    assert entry.details["ok"] is False
    assert entry.details["error"] == "ToolError"


def test_forbidden_call_is_not_recorded(test_user, admin_only_tool):
    tool_error(test_user, admin_only_tool)
    assert not AuditLogEntry.objects.filter(action="mcp_tool_called").exists()
