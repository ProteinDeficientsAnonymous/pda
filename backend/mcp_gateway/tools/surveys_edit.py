from typing import Annotated, Any
from uuid import UUID

import anyio
import anyio.lowlevel
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


def _plan(detail: dict[str, Any], settings: dict[str, Any]) -> Edit:
    """Check every change against the survey before saving any; return the view calls to make."""
    edit = Edit()
    plan_settings(edit, detail, settings)
    return edit


async def _apply(user: User, survey_id: UUID, steps: list[Step]) -> None:
    for step in steps:
        # A cancelled await doesn't stop the view's thread, so let each write finish.
        with anyio.CancelScope(shield=True):
            await call_view(step.view, user, survey_id, *step.args)
        await anyio.lowlevel.checkpoint()


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
    return survey_detail(await call_view(get_survey_view, user, survey_id))
