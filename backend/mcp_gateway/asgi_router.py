from starlette.types import ASGIApp, Receive, Scope, Send

MCP_PATHS = frozenset(
    {
        "/mcp",
        "/authorize",
        "/token",
        "/register",
        "/revoke",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-protected-resource/mcp",
    }
)


class McpDispatcher:
    def __init__(self, django_app: ASGIApp, mcp_app: ASGIApp) -> None:
        self.django_app = django_app
        self.mcp_app = mcp_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Django's ASGIHandler rejects lifespan; the MCP app needs it to run its session manager.
        to_mcp = scope["type"] == "lifespan" or (
            scope["type"] == "http" and scope["path"] in MCP_PATHS
        )
        await (self.mcp_app if to_mcp else self.django_app)(scope, receive, send)
