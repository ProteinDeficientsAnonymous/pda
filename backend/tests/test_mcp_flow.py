import asyncio

import pytest
from mcp_gateway.server import TOOL_PERMISSIONS, pda_mcp, pda_tool
from users.permissions import PermissionKey

from tests._mcp_helpers import connect, mcp_client, rpc

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


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
