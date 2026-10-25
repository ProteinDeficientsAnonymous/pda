from typing import Any
from uuid import UUID

from community._surveys import delete_survey_question as delete_question_view
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.survey_edit_fields import QuestionRef, RemoveQuestion
from mcp_gateway.survey_edit_plan import Edit, Step

Question = dict[str, Any]
_FIELDS = ("label", "field_type", "options", "required", "show_if")
_CONDITION = ("question_id", "operator", "value")


def _named(q: Question) -> str:
    return f'question {q["position"]} ("{q["label"]}")'


def _state(q: Question) -> Question:
    show_if = q["show_if"] and {key: q["show_if"][key] for key in _CONDITION}
    return {**{key: q[key] for key in _FIELDS}, "show_if": show_if or None}


class Questions:
    """Plays the operations through a copy of the survey, so each is checked before any is saved."""

    def __init__(self, edit: Edit, questions: list[Question], answered: bool) -> None:
        self.edit, self.before, self.answered = edit, questions, answered
        self.by_id = {q["id"]: q for q in questions}
        # Each question as the operations so far leave it, in the order the website holds them.
        self.now = {q["id"]: _state(q) for q in questions}
        self.touched: set[str] = set()
        self.diff: list[dict[str, Any]] = []

    def _find(self, ref: QuestionRef) -> Question:
        if isinstance(ref, int):
            if ref > len(self.before):
                raise ToolError(f"there's no question {ref}: the survey has {len(self.before)}")
            return self.before[ref - 1]
        q = self.by_id.get(str(ref))
        if q is None:
            raise ToolError(f"this survey has no question with id {ref}")
        return q

    def _target(self, ref: QuestionRef) -> Question:
        q = self._find(ref)
        if q["id"] in self.touched:
            raise ToolError(f"{_named(q)} is already changed by an earlier operation")
        self.touched.add(q["id"])
        return q

    def _dependents(self, qid: str) -> list[str]:
        return [
            d for d, s in self.now.items() if s["show_if"] and s["show_if"]["question_id"] == qid
        ]

    def remove(self, number: int, op: RemoveQuestion) -> None:
        q = self._target(op.question)
        del self.now[q["id"]]
        cleared = self._dependents(q["id"])
        for d in cleared:
            self.now[d]["show_if"] = None
        if self.answered:
            self.edit.notes.append(f"removing {_named(q)} hides its answers in existing responses")
        if cleared:
            names = ", ".join(f'"{self.now[d]["label"]}"' for d in cleared)
            self.edit.notes.append(f"removing {_named(q)} clears the show_if on {names}")
        self.diff.append({"op": "remove", "position": q["position"], "label": q["label"]})
        label = f"operation {number}: remove {_named(q)}"
        self.edit.steps.append(Step(label, delete_question_view, (UUID(q["id"]),)))

    def finish(self) -> None:
        if self.diff:
            self.edit.changes["questions"] = self.diff
