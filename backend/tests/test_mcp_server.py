import pytest
from asgiref.sync import async_to_sync
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.provider import PdaAccessToken, PdaOAuthProvider
from mcp_gateway.server import (
    TOOL_PERMISSIONS,
    current_user,
    pda_mcp,
    pda_tool,
    require_tool_permission,
)
from users.models import User
from users.permissions import PermissionKey

from tests._mcp_helpers import make_grant, make_tokens

pytestmark = pytest.mark.django_db


def _signed_in(user):
    # Fresh row per sign-in, like the per-request token lookup.
    fresh = User.objects.get(pk=user.pk)
    token = PdaAccessToken(
        token="t", client_id="c", scopes=["pda"], subject=str(user.pk), user=fresh
    )
    return auth_context_var.set(AuthenticatedUser(token))


@pytest.fixture
def as_user():
    tokens = []
    yield lambda user: tokens.append(_signed_in(user))
    for token in reversed(tokens):
        auth_context_var.reset(token)


@pytest.fixture
def admin_only_tool():
    @pda_tool(PermissionKey.MANAGE_USERS)
    async def admin_only() -> str:
        return "secret"

    yield "admin_only"
    pda_mcp.remove_tool("admin_only")
    TOOL_PERMISSIONS.pop("admin_only")


def test_current_user_requires_token():
    with pytest.raises(ToolError):
        async_to_sync(current_user)()


def test_current_user_is_the_tokens_user(test_user, as_user):
    as_user(test_user)
    assert async_to_sync(current_user)().pk == test_user.pk


def test_require_tool_permission(test_user, manage_users_user):
    with pytest.raises(ToolError, match="you don't have permission to do that"):
        async_to_sync(require_tool_permission)(test_user, PermissionKey.MANAGE_USERS)
    async_to_sync(require_tool_permission)(
        manage_users_user, PermissionKey.MANAGE_EVENTS, PermissionKey.MANAGE_USERS
    )


def _tool_names() -> set[str]:
    return {tool.name for tool in async_to_sync(pda_mcp.list_tools)()}


def test_list_tools_filters_by_permission(test_user, manage_users_user, as_user, admin_only_tool):
    as_user(test_user)
    assert admin_only_tool not in _tool_names()
    as_user(manage_users_user)
    assert admin_only_tool in _tool_names()


def test_call_tool_rechecks_permission(test_user, manage_users_user, as_user, admin_only_tool):
    as_user(test_user)
    with pytest.raises(ToolError, match="permission"):
        async_to_sync(pda_mcp.call_tool)(admin_only_tool, {})
    as_user(manage_users_user)
    result = async_to_sync(pda_mcp.call_tool)(admin_only_tool, {})
    assert result.content[0].text == "secret"  # type: ignore[union-attr]


def test_tool_registered_outside_pda_tool_is_hidden_and_denied(test_user, as_user):
    pda_mcp.add_tool(lambda: "x", name="unguarded")
    try:
        as_user(test_user)
        assert "unguarded" not in _tool_names()
        with pytest.raises(ToolError):
            async_to_sync(pda_mcp.call_tool)("unguarded", {})
    finally:
        pda_mcp.remove_tool("unguarded")


def test_whoami_reports_name_roles_and_permissions(manage_users_user, as_user):
    as_user(manage_users_user)
    result = async_to_sync(pda_mcp.call_tool)("whoami", {})
    assert result.structured_content == {  # type: ignore[union-attr]
        "name": "Admin User",
        "roles": ["admin_mgr"],
        "permissions": sorted([PermissionKey.CREATE_USER, PermissionKey.MANAGE_USERS]),
    }


def test_tool_call_reuses_the_user_the_token_lookup_loaded(
    manage_users_user, django_assert_num_queries
):
    access = make_tokens(make_grant(manage_users_user))
    token = async_to_sync(PdaOAuthProvider().load_access_token)(access)
    assert token is not None
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        with django_assert_num_queries(1):
            result = async_to_sync(pda_mcp.call_tool)("whoami", {})
    finally:
        auth_context_var.reset(reset)
    assert result.structured_content["roles"] == ["admin_mgr"]  # type: ignore[union-attr]
