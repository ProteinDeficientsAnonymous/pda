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

from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.survey_edit_fields import SurveyChanges
from mcp_gateway.survey_edit_plan import Edit, Step, plan_settings
from mcp_gateway.tools.surveys_read import _survey_id, survey_detail
from mcp_gateway.view_calls import call_view

logger = logging.getLogger(__name__)
_RELOAD_FAILED = "every change was saved, but the survey couldn't be reloaded: call get_survey"


def _plan(detail: dict[str, Any], settings: dict[str, Any]) -> Edit:
    """Check every change against the survey before saving any; return the view calls to make."""
    edit = Edit()
    plan_settings(edit, detail, settings)
    return edit


def _stopped(steps: list[Step], done: int, exc: Exception) -> ToolError:
    failed = f"{steps[done].label} failed"
    if isinstance(exc, ToolError):
        failed += f": {exc}"
    else:
        # Only a ToolError's text is written for the client; anything else stays in the log.
        logger.exception("update_survey: %s", failed)
        raise exc
    return ToolError(f"nothing was saved: {failed}")


async def _apply(user: User, survey_id: UUID, steps: list[Step]) -> None:
    for done, step in enumerate(steps):
        try:
            # A cancelled await doesn't stop the view's thread, so let each write finish.
            with anyio.CancelScope(shield=True):
                await call_view(step.view, user, survey_id, *step.args)
        # Exception, not BaseException: a cancel lands at the checkpoint, between steps.
        except Exception as exc:
            raise _stopped(steps, done, exc) from exc
        try:
            await checkpoint()
        except anyio.get_cancelled_exc_class():
            applied = [step.label for step in steps[: done + 1]]
            logger.warning("update_survey cancelled on survey %s after %s", survey_id, applied)
            raise


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "edit a switched-off survey's settings in place; send only what changes. it's saved "
        "right away. a switched-on survey can't be edited with this tool yet. to switch a survey "
        "on use publish_survey."
    ),
)
async def update_survey(
    survey: Annotated[str, Field(description="survey id (uuid) or slug, e.g. from list_surveys")],
    settings: Annotated[SurveyChanges | None, Field(description="only what changes")] = None,
) -> dict[str, Any]:
    user = await current_user()
    survey_id = await _survey_id(survey, user)
    before = await call_view(get_survey_view, user, survey_id)
    if before["is_active"]:
        raise ToolError("this survey is switched on: edit it in pda for now")
    changed = settings.model_dump(mode="json", exclude_unset=True) if settings else {}
    if not changed:
        raise ToolError("no changes given")
    edit = _plan(survey_detail(before), changed)
    await _apply(user, survey_id, edit.steps)
    try:
        return survey_detail(await call_view(get_survey_view, user, survey_id))
    except Exception:
        # Everything is saved, so an error here would only invite a retry that saves it twice.
        logger.exception("update_survey saved survey %s but couldn't reload it", survey_id)
        return {"saved": True, "note": _RELOAD_FAILED}
