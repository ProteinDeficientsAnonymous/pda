import asyncio
import base64
import hashlib
import secrets
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.asgi import get_asgi_application
from mcp_gateway.asgi_router import McpDispatcher
from mcp_gateway.models import OAuthAuthRequest
from mcp_gateway.provider import issue_auth_code
from mcp_gateway.server import TOOL_PERMISSIONS, build_mcp_app, pda_mcp, pda_tool
from users.permissions import PermissionKey

from tests._mcp_helpers import REDIRECT

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

BASE = settings.MCP_PUBLIC_BASE_URL
RESOURCE = f"{BASE}/mcp"


@asynccontextmanager
async def mcp_client():
    # A session manager runs once, so each test needs a fresh MCP app.
    app = McpDispatcher(get_asgi_application(), build_mcp_app())
    async with pda_mcp.session_manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
            yield client


async def connect(client: httpx.AsyncClient, user) -> str:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    registration = {"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none"}
    client_id = (await client.post("/register", json=registration)).json()["client_id"]
    authorize = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
        },
    )
    request_id = parse_qs(urlsplit(authorize.headers["location"]).query)["request"][0]
    auth_request = await OAuthAuthRequest.objects.select_related("client").aget(pk=request_id)
    code = await sync_to_async(issue_auth_code)(auth_request, user)
    token = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
    )
    return token.json()["access_token"]


async def rpc(client: httpx.AsyncClient, token: str, method: str, **params) -> httpx.Response:
    return await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
    )


@pytest.fixture
def admin_only_tool():
    @pda_tool(PermissionKey.MANAGE_USERS)
    async def admin_only() -> str:
        return "secret"

    yield "admin_only"
    pda_mcp.remove_tool("admin_only")
    TOOL_PERMISSIONS.pop("admin_only")


def test_full_flow_whoami(manage_users_user):
    async def flow():
        async with mcp_client() as client:
            token = await connect(client, manage_users_user)
            init = await rpc(
                client,
                token,
                "initialize",
                protocolVersion="2025-06-18",
                capabilities={},
                clientInfo={"name": "test", "version": "1"},
            )
            assert init.status_code == 200, init.text
            return (await rpc(client, token, "tools/call", name="whoami", arguments={})).json()

    result = asyncio.run(flow())["result"]
    assert not result.get("isError")
    assert result["structuredContent"]["name"] == "Admin User"
    assert PermissionKey.MANAGE_USERS in result["structuredContent"]["permissions"]


def test_tools_list_filtered_by_permission(test_user, manage_users_user, admin_only_tool):
    async def flow():
        async with mcp_client() as client:
            member, admin = (
                await connect(client, test_user),
                await connect(client, manage_users_user),
            )
            listed = {}
            for label, token in (("member", member), ("admin", admin)):
                tools = (await rpc(client, token, "tools/list")).json()["result"]["tools"]
                listed[label] = {tool["name"] for tool in tools}
            denied = await rpc(client, member, "tools/call", name=admin_only_tool, arguments={})
            return listed, denied.json()["result"]

    listed, denied = asyncio.run(flow())
    assert admin_only_tool not in listed["member"]
    assert admin_only_tool in listed["admin"]
    assert denied["isError"] is True
    assert "permission" in denied["content"][0]["text"]


def test_mcp_paused_user_gets_401(test_user):
    async def flow():
        async with mcp_client() as client:
            token = await connect(client, test_user)
            before = await rpc(client, token, "tools/list")
            test_user.is_paused = True
            await test_user.asave(update_fields=["is_paused"])
            return before, await rpc(client, token, "tools/list")

    before, after = asyncio.run(flow())
    assert before.status_code == 200
    assert after.status_code == 401
