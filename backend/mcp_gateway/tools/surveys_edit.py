import json
import logging
from typing import Annotated, Any
from uuid import UUID

import anyio
from anyio.lowlevel import checkpoint
from community._surveys import get_survey_admin as get_survey_view
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.confirm import Confirmed, ConfirmToken, issue_confirm_token, use_confirm_token
from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.survey_edit_fields import QuestionOps, SurveyChanges
from mcp_gateway.survey_edit_plan import Edit, Step, operation, plan_settings
from mcp_gateway.survey_edit_questions import Questions
from mcp_gateway.tools.surveys_read import _survey_id, survey_detail
from mcp_gateway.view_calls import call_view

logger = logging.getLogger(__name__)
_RELOAD_FAILED = "every change was saved, but the survey couldn't be reloaded: call get_survey"


def _plan(
    detail: dict[str, Any], settings: dict[str, Any], ops: list[Any], orders: dict[str, int]
) -> Edit:
    """Check every change against the survey before saving any; return the view calls to make."""
    edit, count = Edit(), detail["response_count"]
    if count:
        edit.notes.append(f"this survey already has {count} response{'s' * (count != 1)}")
    if settings:
        plan_settings(edit, detail, settings)
    questions = Questions(edit, detail["questions"], bool(count), orders)
    for number, op in enumerate(ops, start=1):
        with operation(number):
            getattr(questions, op.op)(number, op)
    questions.finish()
    if not edit.changes:
        raise ToolError("nothing would change: these values match the survey already")
    return edit


def _preview(bound: Confirmed, edit: Edit) -> dict[str, Any]:
    token = None if edit.blockers else issue_confirm_token(bound)
    return {"changes": edit.changes, "notes": edit.notes + edit.blockers, "confirm_token": token}


async def _stopped(
    user: User, survey_id: UUID, steps: list[Step], done: int, exc: Exception
) -> ToolError:
    failed = f"{steps[done].label} failed"
    if isinstance(exc, ToolError):
        failed += f": {exc}"
    else:
        # Only a ToolError's text is written for the client; anything else stays in the log.
        logger.exception("update_survey: %s", failed)
        if not done:
            raise exc
        failed += " unexpectedly"
    if not done:
        return ToolError(f"nothing was saved: {failed}")
    try:
        survey = survey_detail(await call_view(get_survey_view, user, survey_id))
    except Exception:
        survey = None
    report = {
        "error": f"stopped partway; what was saved stays saved. {failed}",
        "applied": [step.label for step in steps[:done]],
        "not_applied": [step.label for step in steps[done:]],
        "survey": survey,
    }
    return ToolError(json.dumps(report))


async def _apply(user: User, survey_id: UUID, steps: list[Step]) -> None:
    created: dict[str, str] = {}
    for done, step in enumerate(steps):
        try:
            # A cancelled await doesn't stop the view's thread, so let each write finish.
            with anyio.CancelScope(shield=True):
                body = await call_view(step.view, user, survey_id, *step.call_args(created))
        # Exception, not BaseException: a cancel lands at the checkpoint, between steps.
        except Exception as exc:
            raise await _stopped(user, survey_id, steps, done, exc) from exc
        if step.creates:
            created[step.creates] = body["id"]
        try:
            await checkpoint()
        except anyio.get_cancelled_exc_class():
            applied = [step.label for step in steps[: done + 1]]
            logger.warning("update_survey cancelled on survey %s after %s", survey_id, applied)
            raise


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "edit a survey in place: its settings, and add, change, remove or reorder questions. "
        "send only what changes. question positions always mean the survey as it was before this "
        "edit, so read it with get_survey first. a switched-off survey is saved right away. for a "
        "switched-on survey (members may be answering), the first call saves nothing and returns "
        "a before/after diff, notes on side effects and a confirm_token: show the diff and notes, "
        "get an explicit yes, then call again with the same changes and the token. to switch a "
        "survey on use publish_survey."
    ),
)
async def update_survey(
    survey: Annotated[str, Field(description="survey id (uuid) or slug, e.g. from list_surveys")],
    settings: Annotated[SurveyChanges | None, Field(description="only what changes")] = None,
    questions: QuestionOps | None = None,
    confirm_token: ConfirmToken = None,
) -> dict[str, Any]:
    user = await current_user()
    survey_id = await _survey_id(survey, user)
    before = await call_view(get_survey_view, user, survey_id)
    changed = settings.model_dump(mode="json", exclude_unset=True) if settings else {}
    if not (changed or questions):
        raise ToolError("no changes given")
    detail = survey_detail(before)
    orders = {q["id"]: q["display_order"] for q in before["questions"]}
    edit = _plan(detail, changed, questions or [], orders)
    # exclude_unset: an explicit null, like show_if: null, is a change the token must cover.
    ops = [op.model_dump(mode="json", exclude_unset=True) for op in questions or []]
    # status turns on by the clock alone, so it would expire a token for no reason.
    state = {key: value for key, value in detail.items() if key != "status"}
    bound = Confirmed(user.pk, before["id"], "update_survey", [changed, ops], state)
    if confirm_token is not None:
        await use_confirm_token(confirm_token, bound)
    elif before["is_active"]:
        return _preview(bound, edit)
    elif edit.blockers:
        raise ToolError("nothing was saved: " + "; ".join(edit.blockers))
    await _apply(user, survey_id, edit.steps)
    try:
        return survey_detail(await call_view(get_survey_view, user, survey_id))
    except Exception:
        # Everything is saved, so an error here would only invite a retry that saves it twice.
        logger.exception("update_survey saved survey %s but couldn't reload it", survey_id)
        return {"saved": True, "note": _RELOAD_FAILED}
