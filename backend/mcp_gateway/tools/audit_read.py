from typing import Annotated, Any

from audit.api import AuditLogFilters, AuditLogQuery, list_audit_log
from pydantic import Field
from users.permissions import PermissionKey

from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.view_calls import call_view


@pda_tool(
    PermissionKey.VIEW_AUDIT_LOG,
    description=(
        "read the pda audit log, newest first: who did what to whom and when. filters combine "
        "with and. for what happened to a member and who did it, pass filters.member_id (from "
        "find_members or search_members): that covers entries targeting their account plus "
        "their join requests. for recent actions by an admin, pass filters.actor_id. each entry has "
        "action (e.g. join_request_approved, user_paused, user_attendance_paused, "
        "user_archived, user_reactivated), actor_label (who did it; anonymous for public forms "
        "and failed sign-ins), target_type and target_id (what it was done to), details (names, "
        "user_id and other context) and created_at. paged: fetch more with offset=next_offset, "
        "keeping the same filters."
    ),
)
async def audit_history(
    filters: AuditLogFilters | None = None,
    limit: Annotated[int, Field(ge=1, le=100, description="entries per page")] = 50,
    offset: Annotated[
        int, Field(ge=0, le=100_000, description="next_offset from the previous page")
    ] = 0,
) -> dict[str, Any]:
    query = AuditLogQuery(**(filters or AuditLogFilters()).model_dump(), limit=limit, offset=offset)
    return await call_view(list_audit_log, await current_user(), params=query)
