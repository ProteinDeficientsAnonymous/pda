from typing import Any
from uuid import UUID

import anyio
import anyio.lowlevel
from community._surveys import create_survey as create_survey_view
from community._surveys import delete_survey as delete_survey_view
from users.models import User
from users.permissions import PermissionKey

from mcp_gateway.server import current_user, pda_tool
from mcp_gateway.survey_fields import SurveySettings, to_survey_in
from mcp_gateway.tools.surveys_read import survey_detail
from mcp_gateway.view_calls import call_view


async def _shielded(view: Any, user: User, *args: Any) -> Any:
    # A cancelled await doesn't stop the view's thread, so let each write finish before a cancel.
    with anyio.CancelScope(shield=True):
        return await call_view(view, user, *args)


@pda_tool(
    PermissionKey.MANAGE_SURVEYS,
    description=(
        "create a pda survey with no questions yet, switched off: its page shows it closed and "
        "it takes no responses. before calling: show the user the settings and get their ok. "
        "after creating, show the summary and say they add questions and switch it on in pda at "
        "its edit_url."
    ),
)
async def create_survey(settings: SurveySettings) -> dict[str, Any]:
    user = await current_user()
    survey = await _shielded(create_survey_view, user, to_survey_in(settings))
    survey_id = UUID(survey["id"])
    # Every write is shielded, so these checkpoints are where a cancel lands and gets cleaned up.
    try:
        await anyio.lowlevel.checkpoint()
    except BaseException:
        await _shielded(delete_survey_view, user, survey_id)
        raise
    return survey_detail(survey)
