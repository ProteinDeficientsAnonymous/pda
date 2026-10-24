from collections.abc import Callable
from typing import Any, TypeVar
from urllib.parse import urlsplit

from asgiref.sync import sync_to_async
from django.conf import settings
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolResult, InputRequiredResult
from mcp_types import Tool as MCPTool
from starlette.applications import Starlette
from users.models import User

from mcp_gateway.provider import SCOPE, PdaOAuthProvider

BASE_URL = settings.MCP_PUBLIC_BASE_URL
FORBIDDEN = "you don't have permission to do that"
TOOL_PERMISSIONS: dict[str, tuple[str, ...]] = {}

_Fn = TypeVar("_Fn", bound=Callable[..., Any])


async def current_user() -> User:
    token = get_access_token()
    user = None
    if token is not None and token.subject:
        user = await User.objects.prefetch_related("roles").filter(pk=token.subject).afirst()
    if user is None:
        raise ToolError("you're not signed in")
    return user


def _has_any(user: User, keys: tuple[str, ...]) -> bool:
    return any(user.has_permission(key) for key in keys)


def _may_use(user: User, tool_name: str) -> bool:
    # Fail closed: a tool registered without pda_tool has no permission record.
    keys = TOOL_PERMISSIONS.get(tool_name)
    return keys is not None and (not keys or _has_any(user, keys))


async def require_tool_permission(user: User, *keys: str) -> None:
    if not await sync_to_async(_has_any)(user, keys):
        raise ToolError(FORBIDDEN)


class PdaMCPServer(MCPServer):
    async def list_tools(self) -> list[MCPTool]:
        user = await current_user()
        tools = await super().list_tools()
        visible = await sync_to_async(lambda: [t for t in tools if _may_use(user, t.name)])()
        return visible

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Context | None = None
    ) -> CallToolResult | InputRequiredResult:
        user = await current_user()
        if not await sync_to_async(_may_use)(user, name):
            raise ToolError(FORBIDDEN)
        return await super().call_tool(name, arguments, context)


pda_mcp = PdaMCPServer(
    name="pda",
    instructions=(
        "tools for the pda (protein deficients anonymous) community platform. every call acts as "
        "the signed-in member and can only do what that member's roles allow."
    ),
    auth_server_provider=PdaOAuthProvider(),
    auth=AuthSettings(
        issuer_url=BASE_URL,
        resource_server_url=f"{BASE_URL}/mcp",
        validate_token_resource=True,
        required_scopes=[SCOPE],
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]
        ),
        revocation_options=RevocationOptions(enabled=True),
    ),
)


def pda_tool(*permissions: str, **tool_kwargs: Any) -> Callable[[_Fn], _Fn]:
    """Register an MCP tool usable by members holding any of `permissions` (none: any member)."""

    def decorator(fn: _Fn) -> _Fn:
        TOOL_PERMISSIONS[tool_kwargs.get("name") or fn.__name__] = permissions
        return pda_mcp.tool(**tool_kwargs)(fn)

    return decorator


def build_mcp_app() -> Starlette:
    return pda_mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[urlsplit(BASE_URL).netloc], allowed_origins=[BASE_URL]
        ),
    )


mcp_app = build_mcp_app()
