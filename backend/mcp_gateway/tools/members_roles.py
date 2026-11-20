from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.validation import ValidationException
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.api import list_roles as list_roles_view
from users.api import update_user_roles, validate_admin_role_change, validate_member_role_required
from users.models import MembershipStatus, User
from users.permissions import PermissionKey
from users.roles import Role
from users.schemas import UserRolesIn

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view, validation_tool_error


@pda_tool(
    PermissionKey.MANAGE_ROLES,
    PermissionKey.MANAGE_USERS,
    description="list pda roles with their ids, to resolve a role name (e.g. club rep) to an id.",
)
async def list_roles() -> dict[str, Any]:
    roles = await call_view(list_roles_view, await current_user())
    return {"roles": [{k: r[k] for k in ("id", "name", "is_default")} for r in roles]}


def _named(ids: list[str], names: dict[str, str]) -> list[dict[str, str]]:
    return [{"id": rid, "name": names[rid]} for rid in ids]


def _validate_change(member: User, requester: User, role_ids: list[str]) -> None:
    roles = list(Role.objects.filter(pk__in=role_ids))
    try:
        validate_admin_role_change(member, requester, roles)
        validate_member_role_required(roles)
    except ValidationException as exc:
        raise validation_tool_error(exc) from exc


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "add and/or remove roles on one active member, leaving their other roles as they are. "
        "paused and archived members are refused. role ids come from list_roles; only an admin "
        "can grant admin, and the member role can't be removed. the first call changes nothing "
        "and returns the member, their current roles, the resulting roles and a confirm_token: "
        "show that, get an explicit yes, then call again with the same arguments and the token."
    ),
)
async def set_member_roles(
    member_id: Annotated[UUID, Field(description="the member's id, from find_members")],
    add_role_ids: Annotated[list[str] | None, Field(description="role ids to add")] = None,
    remove_role_ids: Annotated[list[str] | None, Field(description="role ids to remove")] = None,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    add_role_ids, remove_role_ids = add_role_ids or [], remove_role_ids or []
    try:
        member = await User.objects.members_or_archived().aget(pk=member_id)
    except User.DoesNotExist:
        raise ToolError(f"no member with id {member_id}") from None
    if member.membership_status != MembershipStatus.ACTIVE_MEMBER:
        raise ToolError(
            f"{member.full_name} is {member.get_membership_status_display()}; "
            "roles can only be changed for active members"
        )
    if not (add_role_ids or remove_role_ids):
        raise ToolError("give add_role_ids and/or remove_role_ids")
    if set(add_role_ids) & set(remove_role_ids):
        raise ToolError("a role can't be both added and removed")

    names = {r["id"]: r["name"] for r in (await call_view(list_roles_view, user))}
    unknown = sorted((set(add_role_ids) | set(remove_role_ids)) - names.keys())
    if unknown:
        raise ToolError(f"unknown role ids: {', '.join(unknown)}; use list_roles")
    current = [str(pk) async for pk in member.roles.order_by("name").values_list("pk", flat=True)]
    new = [rid for rid in [*current, *add_role_ids] if rid not in remove_role_ids]
    new = list(dict.fromkeys(new))
    if set(new) == set(current):
        raise ToolError(f"{member.full_name} already has exactly those roles; nothing to do")

    await sync_to_async(_validate_change)(member, user, new)
    summary = {"id": str(member.pk), "name": member.full_name}
    bound = Confirmed(
        user.pk,
        target_id=str(member.pk),
        action="set_member_roles",
        changes=sorted(new),
        state=sorted(current),
    )
    if confirm_token is None:
        return {
            "member": summary,
            "current_roles": _named(current, names),
            "resulting_roles": _named(new, names),
            "confirm_token": issue_confirm_token(bound),
        }

    await use_confirm_token(confirm_token, bound)
    result = await call_view(
        update_user_roles, user, user_id=str(member.pk), payload=UserRolesIn(role_ids=new)
    )
    return {
        "member": summary,
        "roles": [{"id": r["id"], "name": r["name"]} for r in result["roles"]],
    }
