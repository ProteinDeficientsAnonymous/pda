from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.events.crud import get_event as get_event_view
from community.events.invitations import InviteIn, can_invite_to_event, closed_to_invites
from community.events.invitations import invite_to_event as invite_to_event_view
from community.models import Event, EventStatus
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.helpers import visible_display_name
from users.models import User

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import BASE_URL, FORBIDDEN, current_user, pda_tool
from mcp_gateway.tools.events_write import EventRef
from mcp_gateway.view_calls import call_view

MemberIds = Annotated[
    list[UUID], Field(min_length=1, max_length=100, description="member ids from search_members")
]


_CLOSED = {
    "invite_to_cancelled_event": "this event is cancelled",
    "invite_to_past_event": "this event has already happened",
    "invite_without_rsvp": "this event doesn't take rsvps",
}


def _invitable(user: User, event_id: str, ids: list[UUID]) -> dict[str, str]:
    event = Event.objects.get(pk=event_id)
    closed = closed_to_invites(event)
    if closed:
        raise ToolError(f"{_CLOSED[closed]}, so nobody can be invited")
    if not can_invite_to_event(user, event):
        raise ToolError(FORBIDDEN)
    # The same members the website's invite picker offers.
    members = User.objects.active_members().filter(needs_onboarding=False, pk__in=ids)
    return {str(m.pk): visible_display_name(m, user) for m in members}


@pda_tool(
    description=(
        "invite members to an event, by ids from search_members. the event must take rsvps. hosts "
        "can always invite; other members only when the event lets everyone invite and they've "
        "rsvp'd going or maybe. on a draft, invitees are saved right away and notified when it's "
        "published. on a published event each new invitee gets a notification and an email, so "
        "the first call invites nobody and returns who would be invited plus a confirm_token: "
        "show the names, get an explicit yes, then call again with the same members and the token."
    )
)
async def invite_to_event(
    event: EventRef, member_ids: MemberIds, confirm_token: ConfirmToken = None
) -> dict[str, Any]:
    user = await current_user()
    body = await call_view(get_event_view, user, event_id=event)
    names = await sync_to_async(_invitable)(user, body["id"], member_ids)
    unknown = sorted({str(i) for i in member_ids} - names.keys())
    if unknown:
        raise ToolError(f"no invitable member with id {', '.join(unknown)}: use search_members")
    already = set(body["invited_user_ids"])
    new = sorted(names.keys() - already)
    if not new:
        raise ToolError("everyone listed is already invited")
    invitees = [names[i] for i in new]
    info = {
        "title": body["title"],
        "url": f"{BASE_URL}/events/{body['slug'] or body['id']}",
        "already_invited": sorted(names[i] for i in names.keys() & already),
    }
    if body["status"] != EventStatus.DRAFT:
        bound = Confirmed(user.pk, body["id"], "invite", new, None)
        if confirm_token is None:
            token = issue_confirm_token(bound)
            return {**info, "would_invite": invitees, "confirm_token": token}
        await use_confirm_token(confirm_token, bound)
    payload = InviteIn(user_ids=new)
    await call_view(invite_to_event_view, user, event_id=UUID(body["id"]), payload=payload)
    return {**info, "invited": invitees}
