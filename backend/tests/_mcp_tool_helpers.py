import pytest
from asgiref.sync import async_to_sync
from django.test import TestCase
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.provider import PdaAccessToken
from mcp_gateway.server import pda_mcp
from users.models import User


def signed_in(user):
    # Fresh row per sign-in, like the per-request token lookup.
    fresh = User.objects.get(pk=user.pk)
    token = PdaAccessToken(
        token="t", client_id="c", scopes=["pda"], subject=str(user.pk), user=fresh
    )
    return auth_context_var.set(AuthenticatedUser(token))


def run_tool(user, tool, **arguments):
    reset = signed_in(user)
    try:
        with TestCase.captureOnCommitCallbacks(execute=True):
            return async_to_sync(pda_mcp.call_tool)(tool, arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(reset)


def tool_error(user, tool, **arguments) -> str:
    with pytest.raises(ToolError) as exc_info:
        run_tool(user, tool, **arguments)
    return str(exc_info.value).removeprefix(f"Error executing tool {tool}: ")


def tool_names(user) -> set[str]:
    token = signed_in(user)
    try:
        return {tool.name for tool in async_to_sync(pda_mcp.list_tools)()}
    finally:
        auth_context_var.reset(token)
