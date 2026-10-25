from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from community._survey_schemas import SurveyPatchIn
from community._surveys import update_survey as update_survey_view
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.fields import build
from mcp_gateway.survey_edit_fields import normalize_settings

# The website forces these on a feedback survey, so a change to them would never be saved.
_FEEDBACK_FIXED = ("anonymous", "linked_event_id")


@dataclass(frozen=True)
class Step:
    view: Callable[..., Any]
    args: tuple[Any, ...] = ()


@dataclass
class Edit:
    steps: list[Step] = field(default_factory=list)


def plan_settings(edit: Edit, detail: dict[str, Any], changed: dict[str, Any]) -> None:
    changed = normalize_settings(changed, detail["title"])
    forced = [key for key in _FEEDBACK_FIXED if key in changed and changed[key] != detail[key]]
    if detail["feedback_event_type"] and forced:
        raise ToolError("feedback surveys are always anonymous and never linked to an event")
    edit.steps.append(Step(update_survey_view, (build(SurveyPatchIn, changed),)))
