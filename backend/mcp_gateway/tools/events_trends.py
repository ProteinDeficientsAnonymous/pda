from typing import Annotated, Any, Literal

from asgiref.sync import sync_to_async
from community.attendance.trends import MAX_WINDOW_DAYS, event_trends
from pydantic import Field
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    PermissionKey.MANAGE_USERS,
    name="event_trends",
    description=(
        "event and attendance trends across all events, counts only (no names), for comparing "
        "official, club and community events over the last n days. per bucket (week or month, "
        "by local start date) and event type: events, events_without_attendance_marked (a host "
        "never marked anyone, so attended undercounts them), attended (host-marked attended "
        "rsvps, the primary number), unique_attended_members, avg_attended_per_marked_event, "
        "going_headcount (going rsvps, a fallback when attendance wasn't marked). attended and "
        "going_headcount include plus-ones and public (non-member) rsvps; "
        "unique_attended_members is members only. cancelled, draft, deleted, tbd and "
        "not-yet-ended events are left out."
    ),
)
async def event_trends_tool(
    days: Annotated[int, Field(ge=1, le=MAX_WINDOW_DAYS, description="window length")] = 90,
    bucket: Annotated[Literal["week", "month"], Field(description="bucket size")] = "month",
) -> dict[str, Any]:
    return await sync_to_async(event_trends)(days, bucket)
