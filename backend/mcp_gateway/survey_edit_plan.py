from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from community._survey_schemas import SurveyPatchIn, SurveyQuestionOrderIn
from community._surveys import update_survey as update_survey_view
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.fields import build
from mcp_gateway.survey_edit_fields import normalize_settings, settings_diff

# The website forces these on a feedback survey, so a change to them would never be saved.
_FEEDBACK_FIXED = ("anonymous", "linked_event_id")


@dataclass(frozen=True)
class Step:
    label: str
    view: Callable[..., Any]
    args: tuple[Any, ...] = ()
    # The created question's id is kept under this key, for the reorder step.
    creates: str = ""
    order: tuple[str, ...] = ()

    def call_args(self, created: dict[str, str]) -> tuple[Any, ...]:
        if not self.order:
            return self.args
        return (SurveyQuestionOrderIn(question_ids=[created.get(k, k) for k in self.order]),)


@dataclass
class Edit:
    steps: list[Step] = field(default_factory=list)
    changes: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


@contextmanager
def operation(number: int) -> Iterator[None]:
    try:
        yield
    except ToolError as exc:
        raise ToolError(f"nothing was saved: operation {number}: {exc}") from exc


def plan_settings(edit: Edit, detail: dict[str, Any], changed: dict[str, Any]) -> None:
    changed = normalize_settings(changed, detail["title"])
    forced = [key for key in _FEEDBACK_FIXED if key in changed and changed[key] != detail[key]]
    if detail["feedback_event_type"] and forced:
        raise ToolError("feedback surveys are always anonymous and never linked to an event")
    diff = settings_diff(detail, changed)
    if detail["response_count"] and "anonymous" in diff:
        edit.blockers.append(
            "anonymous can't change once a survey has responses, so pda refuses it: "
            "leave anonymous out"
        )
    if diff:
        edit.changes["settings"] = diff
        payload = build(SurveyPatchIn, {key: changed[key] for key in diff})
        edit.steps.append(Step("settings", update_survey_view, (payload,)))
