from typing import Annotated, Any
from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.api import attendance_pause_preview, update_user
from users.models import User
from users.permissions import PermissionKey
from users.schemas import UserPatchIn

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


async def _member(member_id: UUID) -> User:
    try:
        return await User.objects.members_or_archived().aget(pk=member_id)
    except User.DoesNotExist:
        raise ToolError(f"no member with id {member_id}") from None


@pda_tool(
    PermissionKey.MANAGE_USERS,
    description=(
        "attendance-pause a member (paused=true). paused=false is refused: an attendance pause "
        "lifts only when they check in at an official or club event. "
        "this is the event rqmt pause for members under 2 official or club events in 12 months, "
        "not the guidelines violation pause, which can't be set here. while attendance-paused "
        "they keep tentative access and can still rsvp to official and club events. pausing "
        "drops their rsvps to other upcoming events, takes them off as co-host of any upcoming "
        "event (official and club too) where others host, moves events they host alone back "
        "to draft (guests are told), rescinds their pending co-host invites, and strips their "
        "roles. the first call changes nothing and returns the member, the events affected "
        "(each with a role and outcome: rsvp kept or removed, hosting removed or drafted, "
        "cohost_invite rescinded) and a confirm_token: show "
        "that, get an explicit yes, then call again with the same arguments and the token."
    ),
)
async def set_attendance_pause(
    member_id: Annotated[UUID, Field(description="the member's id, from find_members")],
    paused: Annotated[bool, Field(description="true to pause; false is refused")],
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    member = await _member(member_id)
    summary = {"id": str(member.pk), "name": member.full_name}
    if paused and member.is_attendance_paused:
        raise ToolError(f"{member.full_name} is already attendance-paused; nothing to do")
    if not paused:
        raise ToolError(
            "an attendance pause lifts only when they check in at an official or club event"
        )

    events: list[dict[str, Any]] = []
    if paused:
        preview = await call_view(attendance_pause_preview, user, user_id=member.pk)
        events = preview["events"]
    bound = Confirmed(
        user.pk,
        target_id=str(member.pk),
        action="set_attendance_pause",
        changes=paused,
        state=events,
    )
    if confirm_token is None:
        return {
            "member": summary,
            "paused": paused,
            "events": events,
            "confirm_token": issue_confirm_token(bound),
        }

    await use_confirm_token(confirm_token, bound)
    result = await call_view(
        update_user, user, user_id=str(member.pk), payload=UserPatchIn(attendance_paused=paused)
    )
    return {
        "member": summary,
        "attendance_paused_at": result["attendance_paused_at"],
        "events": events,
    }
