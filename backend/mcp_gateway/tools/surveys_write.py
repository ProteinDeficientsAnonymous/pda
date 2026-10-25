import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any
from uuid import UUID

import anyio
import anyio.lowlevel
from community._survey_schemas import SurveyPatchIn
from community._surveys import create_survey as create_survey_view
from community._surveys import create_survey_question as create_question_view
from community._surveys import delete_survey as delete_survey_view
from community._surveys import get_survey_admin as get_survey_view
from community._surveys import update_survey as update_survey_view
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.survey_fields import SurveyQuestions, SurveySettings, to_question_in, to_survey_in
from mcp_gateway.tools.surveys_read import survey_detail
from mcp_gateway.view_calls import call_view

logger = logging.getLogger(__name__)


@contextmanager
def _question(position: int) -> Iterator[None]:
    try:
        yield
    except ToolError as exc:
        raise ToolError(f"question {position}: {exc}") from exc


async def _shielded(view: Any, user: User, *args: Any) -> Any:
    # A cancelled await doesn't stop the view's thread, so let each write finish before a cancel.
    with anyio.CancelScope(shield=True):
        return await call_view(view, user, *args)


async def _discard(user: User, survey_id: UUID, error: BaseException) -> None:
    try:
        await _shielded(delete_survey_view, user, survey_id)
    except Exception:
        logger.exception(
            "create_survey couldn't remove partial survey %s after %r", survey_id, error
        )
        if not isinstance(error, Exception):
            return
        # Only a ToolError's text is written for the client; anything else stays in the log.
        reason = str(error) if isinstance(error, ToolError) else "an internal error"
        raise ToolError(
            f"creating the survey failed ({reason}) and the partial survey {survey_id} couldn't "
            f"be removed; delete it at {BASE_URL}/admin/surveys/{survey_id}"
        ) from error


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "create a pda survey, switched off: its page shows it closed and it takes no responses. "
        "before calling: map each of the user's questions to a field_type, show them every "
        "question's type, options and show_if plus the settings, and get their ok. after "
        "creating, show the summary with its edit_url and ask whether to switch it on now "
        "(publish_survey) or leave it off for review in pda."
    ),
)
async def create_survey(settings: SurveySettings, questions: SurveyQuestions) -> dict[str, Any]:
    user = await current_user()
    survey_in = to_survey_in(settings)
    payloads = []
    for position, question in enumerate(questions, start=1):
        with _question(position):
            payloads.append(to_question_in(question))
    survey = await _shielded(create_survey_view, user, survey_in)
    survey_id = UUID(survey["id"])
    created: list[dict[str, Any]] = []
    # Every write is shielded, so these checkpoints are where a cancel lands and gets cleaned up.
    try:
        await anyio.lowlevel.checkpoint()
        for position, (source, payload) in enumerate(payloads, start=1):
            if payload.show_if:
                payload.show_if.question_id = UUID(created[source - 1]["id"])
            with _question(position):
                created.append(await _shielded(create_question_view, user, survey_id, payload))
            await anyio.lowlevel.checkpoint()
    except BaseException as exc:
        await _discard(user, survey_id, exc)
        if isinstance(exc, ToolError):
            raise ToolError(f"nothing was saved: {exc}") from exc
        raise
    return survey_detail({**survey, "questions": created})


def _publish_notes(feedback_event_type: str) -> list[str]:
    if not feedback_event_type:
        return []
    return [
        f"this is the feedback survey for {feedback_event_type} events: switching it on starts "
        f"the daily feedback emails, asking members who attended a {feedback_event_type} event in "
        "the past week to fill it in, with a reminder 3 days later"
    ]


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "switch a survey on so it takes responses. the first call returns the survey summary, "
        "notes on side effects and a confirm_token: show the summary and notes, get an explicit "
        "yes, then call again with the token."
    ),
)
async def publish_survey(
    survey: Annotated[UUID, Field(description="survey id, e.g. from create_survey")],
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    body = await call_view(get_survey_view, user, survey)
    if body["is_active"]:
        raise ToolError("this survey is already switched on")
    summary = survey_detail(body)
    bound = Confirmed(user.pk, body["id"], "publish_survey", None, summary)
    if confirm_token is None:
        notes = _publish_notes(body["feedback_event_type"])
        return {**summary, "notes": notes, "confirm_token": issue_confirm_token(bound)}
    await use_confirm_token(confirm_token, bound)
    payload = SurveyPatchIn(is_active=True)
    return survey_detail(await call_view(update_survey_view, user, survey, payload))
