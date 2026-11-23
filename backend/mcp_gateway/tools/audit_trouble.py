from datetime import datetime
from typing import Annotated, Any

from asgiref.sync import sync_to_async
from audit.trouble import CLUSTER_MIN
from audit.trouble import trouble_report as build_trouble_report
from pydantic import Field
from pydantic_core import to_jsonable_python
from users.permissions import PermissionKey

from mcp_gateway.server import pda_tool


@pda_tool(
    PermissionKey.VIEW_AUDIT_LOG,
    description=(
        "spot members who had trouble and failures worth fixing, from the audit log. covers "
        "failure actions (failed sign-ins, permission denials, rejected transitions, failed "
        "rsvp emails, …) between since and until. actions: one row per failure action with "
        "count, first_seen, last_seen, members (user ids, from details.user_id, a user target "
        "or the actor) and the latest samples (ip is a short hash, never the address). "
        f"clusters: the same member_id or ip failing {CLUSTER_MIN}+ times within an hour; "
        "recovered_at is their next success (sign-in, rsvp, password change) after the burst, "
        "null if they got stuck. truncated means the window held too many failures: narrow it."
    ),
)
async def trouble_report(
    since: Annotated[datetime, Field(description="on or after this time; utc unless offset")],
    until: Annotated[
        datetime | None, Field(description="before this time; defaults to now")
    ] = None,
) -> dict[str, Any]:
    report = await sync_to_async(build_trouble_report)(since, until)
    return to_jsonable_python(report)
