from datetime import datetime
from typing import Annotated, Any

from community._surveys import list_surveys_admin
from django.utils import timezone
from pydantic import Field
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.event_fields import _local
from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.view_calls import call_view

_LIST_FIELDS = (
    *("id", "slug", "title", "is_active", "visibility", "max_responses"),
    *("response_count", "linked_event_id"),
)


def _status(survey: dict[str, Any]) -> str:
    """return(str): closed, scheduled, capped or active, like surveyStatus on the frontend."""
    now = timezone.now()
    opens, closes = survey["opens_at"], survey["closes_at"]
    if not survey["is_active"] or (closes and now >= datetime.fromisoformat(closes)):
        return "closed"
    if opens and now < datetime.fromisoformat(opens):
        return "scheduled"
    cap = survey["max_responses"]
    return "capped" if cap is not None and survey["response_count"] >= cap else "active"


def _overview(survey: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _status(survey),
        "opens_at": _local(survey["opens_at"]),
        "closes_at": _local(survey["closes_at"]),
        "url": f"{BASE_URL}/surveys/{survey['slug']}",
        "edit_url": f"{BASE_URL}/admin/surveys/{survey['id']}",
    }


def _row(survey: dict[str, Any]) -> dict[str, Any]:
    return {**{key: survey[key] for key in _LIST_FIELDS}, **_overview(survey)}


async def _surveys(user: User) -> list[dict[str, Any]]:
    rows = await call_view(list_surveys_admin, user)
    return sorted(
        rows, key=lambda s: (datetime.fromisoformat(s["created_at"]), s["id"]), reverse=True
    )


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "list every survey, newest first, with its status (active, scheduled, capped or closed), "
        "window (new york local time) and response count. use it to find a survey's id before "
        "reading or editing it. event feedback surveys have no public link: check get_survey "
        "before sharing a url. results are paged: only fetch the next page (offset=next_offset) "
        "if the survey you need isn't on this one."
    ),
)
async def list_surveys(
    limit: Annotated[int, Field(ge=1, le=50, description="surveys per page")] = 20,
    offset: Annotated[int, Field(ge=0, description="next_offset from the previous page")] = 0,
) -> dict[str, Any]:
    rows = await _surveys(await current_user())
    more = offset + limit < len(rows)
    return {
        "surveys": [_row(s) for s in rows[offset : offset + limit]],
        "next_offset": offset + limit if more else None,
    }
