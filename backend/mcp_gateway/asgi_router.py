from asgiref.sync import ThreadSensitiveContext
from django.core.signals import request_finished, request_started
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
        if scope["type"] == "lifespan":
            await self.mcp_app(scope, receive, send)
        elif scope["type"] == "http" and scope["path"] in MCP_PATHS:
            await self._handle_mcp(scope, receive, send)
        else:
            await self.django_app(scope, receive, send)

    async def _handle_mcp(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Mirror ASGIHandler: per-request sync thread and DB connection health checks.
        async with ThreadSensitiveContext():
            await request_started.asend(sender=self.__class__, scope=scope)
            try:
                await self.mcp_app(scope, receive, send)
            finally:
                await request_finished.asend(sender=self.__class__)
