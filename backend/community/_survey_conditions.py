"""Conditional survey questions: `show_if` authoring rules and visibility."""

from collections.abc import Iterable, Mapping
from uuid import UUID

from community._survey_schemas import ShowIfIn
from community._validation import Code, raise_validation
from community.models import (
    CONDITION_SOURCE_TYPES,
    QuestionType,
    ShowIfOperator,
    SurveyQuestion,
)

BOOLEAN_CONDITION_VALUES = ("yes", "no")

SHOW_IF_FIELD = "show_if"


def condition_values(source: SurveyQuestion) -> list[str]:
    """Values a condition on `source` may compare against."""
    if source.field_type == QuestionType.BOOLEAN:
        return list(BOOLEAN_CONDITION_VALUES)
    return list(source.options or [])


def validate_show_if(
    payload: ShowIfIn | None,
    *,
    survey_id: UUID,
    display_order: int,
) -> dict | None:
    """Check a `show_if` payload and return the dict to persist (None to clear).

    payload(ShowIfIn | None): condition the author submitted
    survey_id(UUID): survey the edited question belongs to
    display_order(int): position the edited question will hold
    return(dict | None): normalized condition, or None
    """
    if payload is None:
        return None
    source = SurveyQuestion.objects.filter(survey_id=survey_id, id=payload.question_id).first()
    if source is None:
        raise_validation(
            Code.Survey.CONDITION_QUESTION_NOT_FOUND, field=SHOW_IF_FIELD, status_code=400
        )
    if source.display_order >= display_order:
        raise_validation(
            Code.Survey.CONDITION_QUESTION_NOT_EARLIER, field=SHOW_IF_FIELD, status_code=400
        )
    if source.field_type not in CONDITION_SOURCE_TYPES:
        raise_validation(
            Code.Survey.CONDITION_TYPE_NOT_SUPPORTED,
            field=SHOW_IF_FIELD,
            status_code=400,
            label=source.label,
        )
    if payload.operator == ShowIfOperator.CONTAINS and source.field_type != QuestionType.CHECKBOX:
        raise_validation(
            Code.Survey.CONDITION_OPERATOR_NOT_SUPPORTED,
            field=SHOW_IF_FIELD,
            status_code=400,
            operator=str(payload.operator),
        )
    if payload.value not in condition_values(source):
        raise_validation(
            Code.Survey.CONDITION_VALUE_INVALID,
            field=SHOW_IF_FIELD,
            status_code=400,
            label=source.label,
        )
    return {
        "question_id": str(payload.question_id),
        "operator": str(payload.operator),
        "value": payload.value,
    }


def assert_order_keeps_dependencies(
    questions: Iterable[SurveyQuestion], ordered_ids: list[str]
) -> None:
    """Reject an order that would place a question above the one it depends on."""
    position = {qid: idx for idx, qid in enumerate(ordered_ids)}
    for q in questions:
        if not q.show_if:
            continue
        own = position.get(str(q.id))
        source = position.get(str(q.show_if.get("question_id")))
        if own is None or source is None or source < own:
            continue
        raise_validation(
            Code.Survey.CONDITION_ORDER_CONFLICT,
            field="question_ids",
            status_code=400,
            label=q.label,
        )


def clear_dependent_conditions(survey_id: UUID, question_id: UUID) -> None:
    """Drop `show_if` from questions that pointed at a now-deleted question."""
    dependents = [
        q
        for q in SurveyQuestion.objects.filter(survey_id=survey_id)
        if q.show_if and str(q.show_if.get("question_id")) == str(question_id)
    ]
    for q in dependents:
        q.show_if = None
    if dependents:
        SurveyQuestion.objects.bulk_update(dependents, ["show_if"])


def _condition_met(answer: str, operator: str, value: str) -> bool:
    if operator == ShowIfOperator.CONTAINS:
        return value in [v.strip() for v in answer.split(",") if v.strip()]
    if operator == ShowIfOperator.NOT_EQUALS:
        return answer != value
    return answer == value


def visible_question_ids(
    questions: Mapping[str, SurveyQuestion],
    answers: Mapping[str, str | dict[str, str]],
) -> set[str]:
    """Ids of questions the respondent should see, given their answers.

    A condition pointing at a hidden question is never met, so hiding
    cascades down a chain of dependents.
    """
    visible: set[str] = set()
    ordered = sorted(questions.items(), key=lambda item: item[1].display_order)
    for q_id, q in ordered:
        condition = q.show_if
        if not condition:
            visible.add(q_id)
            continue
        source_id = str(condition.get("question_id", ""))
        if source_id not in visible:
            continue
        answer = answers.get(source_id)
        if not isinstance(answer, str):
            answer = ""
        if _condition_met(
            answer,
            str(condition.get("operator", ShowIfOperator.EQUALS)),
            str(condition.get("value", "")),
        ):
            visible.add(q_id)
    return visible
