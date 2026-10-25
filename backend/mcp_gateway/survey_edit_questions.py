from typing import Any
from uuid import UUID

from community._survey_conditions import condition_still_valid
from community._survey_schemas import SurveyQuestionIn
from community._surveys import delete_survey_question as delete_question_view
from community._surveys import update_survey_question as update_question_view
from community.models import QuestionType, SurveyQuestion
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.fields import build
from mcp_gateway.survey_edit_fields import (
    EditQuestionFields,
    QuestionRef,
    RemoveQuestion,
    UpdateQuestion,
)
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

    def _fits(self, condition: dict[str, Any]) -> bool:
        source = self.now[condition["question_id"]]
        shape = SurveyQuestion(field_type=source["field_type"], options=source["options"])
        return condition_still_valid(condition, shape)

    def _merged(self, q: Question, changes: dict[str, Any]) -> dict[str, Any]:
        state, show_if = self.now[q["id"]], self.now[q["id"]]["show_if"]
        if show_if:
            position = self.by_id[show_if["question_id"]]["position"]
            show_if = {"position": position, **{key: show_if[key] for key in _CONDITION[1:]}}
        merged = {**state, "show_if": show_if, **changes}
        # Stored options are already shaped; only reshape when the type or options change.
        if not {"field_type", "options"} & changes.keys():
            return merged
        if "options" not in changes and state["field_type"] == QuestionType.DATETIME_POLL:
            # Stored in utc; the input model takes new york time and converts it back.
            merged["options"] = [t or o for t, o in zip(q["option_times"], state["options"])]
        return build(EditQuestionFields, merged).model_dump(mode="json")

    def _payload(self, fields: dict[str, Any]) -> SurveyQuestionIn:
        data = {key: fields[key] for key in _FIELDS[:-1]}
        if show_if := fields["show_if"]:
            source = self._find(show_if["position"])
            data["show_if"] = {**show_if, "question_id": source["id"]}
            del data["show_if"]["position"]
        return build(SurveyQuestionIn, data)

    def _shown(self, payload: SurveyQuestionIn) -> dict[str, Any]:
        after = payload.model_dump(mode="json", include=set(_FIELDS))
        if payload.show_if:
            source = self.by_id[str(payload.show_if.question_id)]
            position = {"question_position": source["position"], "question": source["label"]}
            after["show_if"] = {**after["show_if"], **position}
        return after

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

    def update(self, number: int, op: UpdateQuestion) -> None:
        q = self._target(op.question)
        changes = op.changes.model_dump(mode="json", include=op.changes.model_fields_set)
        if "show_if" in changes:
            raise ToolError("show_if can't be changed here yet: edit it in pda")
        payload = self._payload(self._merged(q, changes))
        self.now[q["id"]] = payload.model_dump(mode="json")
        self._keeps_dependents(q)
        if self._diff_update(q, payload):
            label = f"operation {number}: update {_named(q)}"
            self.edit.steps.append(Step(label, update_question_view, (UUID(q["id"]), payload)))

    def _diff_update(self, q: Question, payload: SurveyQuestionIn) -> bool:
        before, after = {key: q[key] for key in _FIELDS}, self._shown(payload)
        changed = {
            k: {"before": before[k], "after": after[k]} for k in _FIELDS if before[k] != after[k]
        }
        if changed:
            entry = {"op": "update", "position": q["position"], "label": q["label"]}
            self.diff.append({**entry, "changes": changed})
        if self.answered and {"field_type", "options"} & changed.keys():
            self.edit.notes.append(
                f"changing the type or options of {_named(q)} may leave existing answers to it "
                "that don't fit"
            )
        return bool(changed)

    def _keeps_dependents(self, q: Question) -> None:
        broken = [
            f'"{self.now[d]["label"]}"'
            for d in self._dependents(q["id"])
            if not self._fits(self.now[d]["show_if"])
        ]
        if broken:
            raise ToolError(
                f"this breaks the show_if on {', '.join(broken)}: change or remove those "
                "conditions in an earlier operation"
            )

    def finish(self) -> None:
        if self.diff:
            self.edit.changes["questions"] = self.diff
