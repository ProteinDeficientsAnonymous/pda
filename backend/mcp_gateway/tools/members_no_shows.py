from typing import Any

from asgiref.sync import sync_to_async
from community.attendance.no_shows import (
    RECENT_RSVP_LIMIT,
    REPEATED_NO_SHOW_MIN,
    members_with_repeated_no_shows,
)
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool


def repeated_no_shows_list() -> dict[str, Any]:
    rows = members_with_repeated_no_shows()
    return {"members": [r.model_dump(mode="json") for r in rows], "total": len(rows)}


@pda_tool(
    PermissionKey.MANAGE_EVENTS,
    description=(
        f"list members with {REPEATED_NO_SHOW_MIN} or more no-shows, for check-in outreach. a "
        "no-show is a host marking the member didn't go at a qualifying event: an official or "
        "club event (community events don't count), as on the members analytics screen; "
        "cancelled, draft and deleted events and events with no start time never count. archived "
        "members are left out. most no-shows first. each row has user_id, full_name, "
        "no_show_count, last_no_show (their latest no-show event) and recent_rsvps: their last "
        f"{RECENT_RSVP_LIMIT} rsvps at qualifying events that have started, newest first, with "
        "the rsvp status and the attendance a host marked (unknown until marked), so a run of "
        "no-shows in a row stands out."
    ),
)
async def repeated_no_shows() -> dict[str, Any]:
    return await sync_to_async(repeated_no_shows_list)()
