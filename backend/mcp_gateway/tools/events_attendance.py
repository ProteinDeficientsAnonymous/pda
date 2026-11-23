from typing import Annotated, Any
from uuid import UUID

from asgiref.sync import sync_to_async
from community.events.host_actions import markable_rsvp, set_attendance
from community.events.schemas import AttendanceIn
from community.models import AttendanceStatus
from community.validation import ValidationException
from pydantic import Field
from users.helpers import visible_display_name
from users.models import User

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view, validation_tool_error


def _current_mark(user: User, event_id: UUID, member_id: UUID, payload: AttendanceIn) -> dict:
    rsvp = markable_rsvp(user, event_id, member_id, payload)
    return {
        "event": rsvp.event.title,
        "member": visible_display_name(rsvp.user, user),
        "for_plus_one": payload.for_plus_one,
        "was": rsvp.plus_one_attendance if payload.for_plus_one else rsvp.attendance,
    }


@pda_tool(
    description=(
        "set or clear a guest's attendance mark on an event, like the host check-in screen: "
        "attended, didnt_go (only for a going rsvp) or unknown (clears the mark and check-in "
        "time). for_plus_one marks their plus one instead. needs the right to edit the event, "
        "and check-in must be open (from 1 hour before start). marking a non-member attended "
        "can make them a member and email them. the first call changes nothing and returns the "
        "current and new mark plus a confirm_token: show that, get an explicit yes, then call "
        "again with the same arguments and the token."
    )
)
async def set_event_attendance(
    event_id: Annotated[UUID, Field(description="event id, e.g. from member_rsvps")],
    member_id: Annotated[UUID, Field(description="the guest's member id, from find_members")],
    attendance: AttendanceStatus,
    for_plus_one: bool = False,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    payload = AttendanceIn(attendance=attendance, for_plus_one=for_plus_one)
    try:
        info = await sync_to_async(_current_mark)(user, event_id, member_id, payload)
    except ValidationException as exc:
        raise validation_tool_error(exc) from exc
    bound = Confirmed(
        user.pk,
        target_id=f"{event_id}:{member_id}",
        action="set_event_attendance",
        changes=payload.model_dump(mode="json"),
        state=info["was"],
    )
    if confirm_token is None:
        return {**info, "attendance": attendance, "confirm_token": issue_confirm_token(bound)}

    await use_confirm_token(confirm_token, bound)
    await call_view(set_attendance, user, event_id=event_id, user_id=member_id, payload=payload)
    return {**info, "attendance": attendance}
