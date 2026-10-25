from typing import Any
from uuid import UUID

from community._survey_conditions import condition_still_valid
from community._survey_schemas import SurveyQuestionIn
from community._surveys import create_survey_question as create_question_view
from community._surveys import delete_survey_question as delete_question_view
from community._surveys import reorder_survey_questions as reorder_view
from community._surveys import update_survey_question as update_question_view
from community.models import QuestionType, SurveyQuestion
from mcp.server.mcpserver.exceptions import ToolError

from mcp_gateway.fields import build
from mcp_gateway.survey_edit_fields import (
    AddQuestion,
    EditQuestionFields,
    QuestionRef,
    RemoveQuestion,
    ReorderQuestions,
    UpdateQuestion,
)
from mcp_gateway.survey_edit_plan import Edit, Step

Question = dict[str, Any]
_FIELDS = ("label", "field_type", "options", "description", "required", "show_if")
# Stored options are already shaped; only re-check the question when these change.
_RECHECK = {"field_type", "options", "description"}
_CONDITION = ("question_id", "operator", "value")


def _named(q: Question) -> str:
    return f'question {q["position"]} ("{q["label"]}")'


def _state(q: Question) -> Question:
    show_if = q["show_if"] and {key: q["show_if"][key] for key in _CONDITION}
    return {**{key: q[key] for key in _FIELDS}, "show_if": show_if or None}


class Questions:
    """Plays the operations through a copy of the survey, so each is checked before any is saved."""

    def __init__(
        self, edit: Edit, questions: list[Question], answered: bool, orders: dict[str, int]
    ) -> None:
        self.edit, self.before, self.answered, self.orders = edit, questions, answered, orders
        self.by_id = {q["id"]: q for q in questions}
        # Each question as the operations so far leave it, in the order the website holds them.
        self.now = {q["id"]: _state(q) for q in questions}
        self.touched: set[str] = set()
        self.refs: list[tuple[int, Question]] = []
        self.anchors: list[tuple[str, Any]] = []
        self.order: tuple[int, list[str]] | None = None
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

    def _ref(self, number: int, ref: QuestionRef) -> Question:
        q = self._find(ref)
        self.refs.append((number, q))
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
        if not _RECHECK & changes.keys():
            return merged
        if "options" not in changes and state["field_type"] == QuestionType.DATETIME_POLL:
            # Stored in utc; the input model takes new york time and converts it back.
            merged["options"] = [t or o for t, o in zip(q["option_times"], state["options"])]
        return build(EditQuestionFields, merged).model_dump(mode="json")

    def _payload(
        self, fields: dict[str, Any], below: int
    ) -> tuple[SurveyQuestionIn, Question | None]:
        """return(tuple): the payload, and its show_if source (which must sit above `below`)."""
        data, source = {key: fields[key] for key in _FIELDS[:-1]}, None
        if show_if := fields["show_if"]:
            source = self._find(show_if["position"])
            if source["id"] not in self.now:
                raise ToolError(f"show_if points at {_named(source)}, which this edit removes")
            if source["position"] >= below:
                raise ToolError(
                    "show_if must point at a question above it in the survey as it is now; to "
                    "depend on a later question, reorder it above in a separate call first"
                )
            data["show_if"] = {**show_if, "question_id": source["id"]}
            del data["show_if"]["position"]
            if not self._fits(data["show_if"]):
                raise ToolError(
                    f"show_if doesn't fit {_named(source)}: compare with one of its options "
                    "(yes/no for a boolean), and use contains only on a checkbox question"
                )
        return build(SurveyQuestionIn, data), source

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
        payload, source = self._payload(self._merged(q, changes), below=q["position"])
        # An unchanged condition is cleared, not refused, when this edit removes its source.
        if source and "show_if" in changes:
            self.refs.append((number, source))
        # Legacy rows can share a display_order, and the website refuses a source that isn't lower.
        if source and self.orders[source["id"]] >= self.orders[q["id"]]:
            raise ToolError(f"{_named(source)} shares this question's stored place: reorder first")
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

    def add(self, number: int, op: AddQuestion) -> None:
        key = f"new question from operation {number}"
        payload, source = self._payload(op.question.model_dump(mode="json"), len(self.before) + 1)
        if source:
            self.refs.append((number, source))
        anchor, after = op.after, "last" if op.after is None else "first"
        if op.after not in (None, 0):
            q = self._ref(number, op.after)
            anchor, after = q["id"], {"position": q["position"], "label": q["label"]}
        self.now[key] = payload.model_dump(mode="json")
        self.anchors.append((key, anchor))
        self.diff.append({"op": "add", "question": self._shown(payload), "after": after})
        label = f'operation {number}: add "{payload.label}"'
        self.edit.steps.append(Step(label, create_question_view, (payload,), creates=key))

    def reorder(self, number: int, op: ReorderQuestions) -> None:
        if self.order is not None:
            raise ToolError("send at most one reorder")
        self.order = number, [self._ref(number, ref)["id"] for ref in op.order]

    def _final_order(self) -> list[str]:
        base = [qid for qid in self.now if qid in self.by_id]
        if self.order is not None:
            number, listed = self.order
            if sorted(listed) != sorted(base):
                raise ToolError(
                    f"nothing was saved: operation {number}: list every question that stays, "
                    "each once"
                )
            base = listed
        placed: dict[Any, list[str]] = {}
        for key, anchor in self.anchors:
            placed.setdefault(anchor, []).append(key)
        final = list(placed.get(0, []))
        for qid in base:
            final += [qid, *placed.get(qid, [])]
        return final + placed.get(None, [])

    def _check_dependencies(self, final: list[str]) -> None:
        index = {qid: i for i, qid in enumerate(final)}
        for qid in final:
            show_if = self.now[qid]["show_if"]
            if show_if and index[show_if["question_id"]] > index[qid]:
                raise ToolError(
                    f'nothing was saved: "{self.now[qid]["label"]}" would come before '
                    f'"{self.now[show_if["question_id"]]["label"]}", which its show_if depends on'
                )

    def finish(self) -> None:
        for number, q in self.refs:
            if q["id"] not in self.now:
                raise ToolError(f"nothing was saved: operation {number}: {_named(q)} is removed")
        final = self._final_order()
        self._check_dependencies(final)
        if final != list(self.now):
            labels = [self.now[qid]["label"] for qid in final]
            self.edit.changes["order"] = {
                "before": [q["label"] for q in self.before],
                "after": labels,
            }
            step = Step("put the questions in their new order", reorder_view, order=tuple(final))
            self.edit.steps.append(step)
        if self.diff:
            self.edit.changes["questions"] = self.diff
