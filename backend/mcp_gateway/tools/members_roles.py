from typing import Any

from users.api import list_roles as list_roles_view
from users.permissions import PermissionKey

from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


@pda_tool(
    PermissionKey.MANAGE_ROLES,
    PermissionKey.MANAGE_USERS,
    description="list pda roles with their ids, to resolve a role name (e.g. club rep) to an id.",
)
async def list_roles() -> dict[str, Any]:
    roles = await call_view(list_roles_view, await current_user())
    return {"roles": [{k: r[k] for k in ("id", "name", "is_default")} for r in roles]}
