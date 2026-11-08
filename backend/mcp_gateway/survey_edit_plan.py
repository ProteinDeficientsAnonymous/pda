from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from community.surveys.crud import update_survey as update_survey_view
from community.surveys.schemas import SurveyPatchIn, SurveyQuestionOrderIn
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.fields import build
from mcp_gateway.survey_edit_fields import normalize_settings, settings_diff
from mcp_gateway.survey_fields import feedback_emails


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


def _force_anonymous(detail: dict[str, Any], changed: dict[str, Any]) -> dict[str, Any]:
    # The website forces anonymous on a feedback survey, so any other value would never be saved.
    if changed.get("anonymous") is False:
        raise ToolError("feedback surveys are always anonymous")
    if not detail["anonymous"] and detail["response_count"]:
        raise ToolError(
            "feedback surveys are always anonymous, and anonymous can't change once a survey "
            "has responses"
        )
    return {**changed, "anonymous": True}


def plan_settings(edit: Edit, detail: dict[str, Any], changed: dict[str, Any]) -> None:
    changed = normalize_settings(changed, detail["title"])
    feedback = changed.get("feedback_event_type", detail["feedback_event_type"])
    if feedback:
        changed = _force_anonymous(detail, changed)
    diff = settings_diff(detail, changed)
    if "feedback_event_type" in diff and feedback and detail["is_active"]:
        edit.notes.append(
            f"making this the feedback survey for {feedback} events starts "
            + feedback_emails(feedback)
        )
    if detail["response_count"] and "anonymous" in diff:
        edit.blockers.append(
            "anonymous can't change once a survey has responses, so pda refuses it: "
            "leave anonymous out"
        )
    if diff:
        edit.changes["settings"] = diff
        payload = build(SurveyPatchIn, {key: changed[key] for key in diff})
        edit.steps.append(Step("settings", update_survey_view, (payload,)))
