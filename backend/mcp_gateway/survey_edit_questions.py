from typing import Any
from uuid import UUID

from community._surveys import delete_survey_question as delete_question_view
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.survey_edit_fields import QuestionRef, RemoveQuestion
from mcp_gateway.survey_edit_plan import Edit, Step

Question = dict[str, Any]


def _named(q: Question) -> str:
    return f'question {q["position"]} ("{q["label"]}")'


class Questions:
    """Plays the operations through a copy of the survey, so each is checked before any is saved."""

    def __init__(self, edit: Edit, questions: list[Question]) -> None:
        self.edit, self.before = edit, questions
        self.by_id = {q["id"]: q for q in questions}
        self.touched: set[str] = set()

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

    def remove(self, number: int, op: RemoveQuestion) -> None:
        q = self._target(op.question)
        label = f"operation {number}: remove {_named(q)}"
        self.edit.steps.append(Step(label, delete_question_view, (UUID(q["id"]),)))
