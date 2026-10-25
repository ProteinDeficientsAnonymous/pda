from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from community._surveys import get_survey_admin, list_surveys_admin
from community.models import SurveyQuestionType
from django.utils import timezone
from pydantic import Field
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.event_fields import _local
from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.view_calls import _tool_error, call_view

_LIST_FIELDS = (
    *("id", "slug", "title", "is_active", "visibility", "max_responses"),
    *("response_count", "linked_event_id"),
)
_SETTINGS = (
    *("id", "slug", "title", "description", "visibility", "is_active", "one_response_per_user"),
    *("anonymous", "confirmation_message", "max_responses", "linked_event_id"),
    *("feedback_event_type", "response_count"),
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
        "edit_url": f"{BASE_URL}/admin/surveys/{survey['id']}",
    }


def _row(survey: dict[str, Any]) -> dict[str, Any]:
    return {**{key: survey[key] for key in _LIST_FIELDS}, **_overview(survey)}


def _option_time(option: str) -> str | None:
    # API clients other than the frontend can store options that aren't offset-aware ISO times.
    try:
        aware = datetime.fromisoformat(option).tzinfo is not None
    except ValueError:
        return None
    return _local(option) if aware else None


def _question(
    q: dict[str, Any], position: int, sources: dict[str, tuple[int, str]]
) -> dict[str, Any]:
    row = {key: q[key] for key in ("id", "label", "field_type", "options", "required")}
    if q["field_type"] == SurveyQuestionType.DATETIME_POLL:
        row["option_times"] = [_option_time(option) for option in q["options"]]
    show_if = q["show_if"]
    if show_if:
        source_position, source_label = sources.get(show_if["question_id"], (None, None))
        show_if = {**show_if, "question_position": source_position, "question": source_label}
    return {**row, "position": position, "show_if": show_if}


def _questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = {q["id"]: (i, q["label"]) for i, q in enumerate(questions, 1)}
    return [_question(q, i, sources) for i, q in enumerate(questions, 1)]


async def _surveys(user: User) -> list[dict[str, Any]]:
    rows = await call_view(list_surveys_admin, user)
    return sorted(
        rows, key=lambda s: (datetime.fromisoformat(s["created_at"]), s["id"]), reverse=True
    )


async def _survey_id(ref: str, user: User) -> UUID:
    try:
        parsed = UUID(ref)
    except ValueError:
        parsed = None
    # UUID() also takes dashless and braced forms, which could be a hex-looking slug.
    if parsed is not None and str(parsed) == ref.lower():
        return parsed
    match = next((s for s in await _surveys(user) if s["slug"] == ref), None)
    if match is None:
        raise _tool_error(404, f"no survey with id or slug {ref}")
    return UUID(match["id"])


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "list every survey, newest first, with its status (active, scheduled, capped or closed), "
        "window (new york local time) and response count. use it to find a survey's id before "
        "reading or editing it, and use get_survey for a survey's public link. results are "
        "paged: only fetch the next page (offset=next_offset) if the survey you need isn't on "
        "this one."
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


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "read one survey's settings and its questions in display order, by id or slug. use it "
        "before editing a survey or its questions; show_if names the question it depends on. "
        "url is null for event feedback surveys, which members only reach through their emailed "
        "link."
    ),
)
async def get_survey(
    survey: Annotated[str, Field(description="survey id (uuid) or slug, e.g. from list_surveys")],
) -> dict[str, Any]:
    user = await current_user()
    body = await call_view(get_survey_admin, user, survey_id=await _survey_id(survey, user))
    public = not body["feedback_event_type"]
    return {
        **{key: body[key] for key in _SETTINGS},
        **_overview(body),
        "url": f"{BASE_URL}/surveys/{body['slug']}" if public else None,
        "questions": _questions(body["questions"]),
    }
