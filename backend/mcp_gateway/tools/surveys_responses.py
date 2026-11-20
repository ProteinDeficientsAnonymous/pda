from typing import Annotated, Any

from community.models import SurveyQuestionType
from community.surveys.crud import get_survey_admin
from community.surveys.responses import list_survey_responses
from pydantic import Field
from users.permissions import PermissionKey

from mcp_gateway.fields import local_time
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.tools.surveys_read import resolve_survey_id
from mcp_gateway.view_calls import call_view

_EMPTY = (None, "", [], {})


def _answer(response: dict[str, Any], qid: str, anonymous: bool) -> dict[str, Any] | None:
    answer = (response["answers"].get(qid) or {}).get("answer")
    if answer in _EMPTY:
        return None
    submitted = local_time(response["submitted_at"]) or ""
    row: dict[str, Any] = {
        "answer": answer,
        "submitted_at": submitted[:10] if anonymous else submitted,
    }
    if not anonymous:
        row["respondent"] = response["user_name"]
    if response["event_title"]:
        row["event"] = response["event_title"]
    return row


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "read a survey's responses by id or slug, grouped per question in display order, newest "
        "first. anonymous surveys leave out who answered and give only the day submitted. "
        "results are paged by response: fetch the next page with offset=next_offset."
    ),
)
async def get_survey_responses(
    survey: Annotated[str, Field(description="survey id (uuid) or slug, e.g. from list_surveys")],
    limit: Annotated[int, Field(ge=1, le=100, description="responses per page")] = 50,
    offset: Annotated[int, Field(ge=0, description="next_offset from the previous page")] = 0,
) -> dict[str, Any]:
    user = await current_user()
    survey_id = await resolve_survey_id(survey)
    body = await call_view(get_survey_admin, user, survey_id=survey_id)
    responses = await call_view(list_survey_responses, user, survey_id=survey_id)
    page = responses[offset : offset + limit]
    anonymous = body["anonymous"]
    questions = []
    for q in body["questions"]:
        if q["field_type"] == SurveyQuestionType.SECTION:
            continue
        rows = (_answer(r, q["id"], anonymous) for r in page)
        questions.append(
            {
                **{key: q[key] for key in ("id", "label", "field_type")},
                "answers": [row for row in rows if row],
            }
        )
    more = offset + limit < len(responses)
    return {
        "survey": {key: body[key] for key in ("id", "slug", "title", "anonymous")},
        "response_count": len(responses),
        "next_offset": offset + limit if more else None,
        "questions": questions,
    }
