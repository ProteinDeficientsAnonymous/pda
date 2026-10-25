"""Answer validation logic for survey responses."""

from collections.abc import Callable

from community._question_answers import (
    assert_checkbox_members,
    assert_single_choice_member,
    checkbox_values,
    is_answer_empty,
)
from community._survey_conditions import visible_question_ids
from community._validation import Code, raise_validation
from community.models import PollAvailability, SurveyQuestion, SurveyQuestionType


def _validate_choice_answer(answer: str, q: SurveyQuestion) -> None:
    assert_single_choice_member(
        answer,
        q.options,
        code=Code.Survey.ANSWER_INVALID_OPTION,
        field=f"answers.{q.id}",
        label=q.label,
    )


def _validate_checkbox_answer(answer: str | list[str], q: SurveyQuestion) -> None:
    assert_checkbox_members(
        answer,
        q.options,
        code=Code.Survey.ANSWER_INVALID_OPTION,
        field=f"answers.{q.id}",
        label=q.label,
    )


def _validate_number_answer(answer: str, q: SurveyQuestion) -> None:
    try:
        float(answer)
    except ValueError:
        raise_validation(
            Code.Survey.ANSWER_MUST_BE_NUMBER,
            field=f"answers.{q.id}",
            label=q.label,
        )


def _validate_boolean_answer(answer: str, q: SurveyQuestion) -> None:
    if answer not in ("yes", "no"):
        raise_validation(
            Code.Survey.ANSWER_MUST_BE_BOOLEAN,
            field=f"answers.{q.id}",
            label=q.label,
        )


def _validate_rating_answer(answer: str, q: SurveyQuestion) -> None:
    try:
        val = int(answer)
        if val < 1 or val > 5:
            raise_validation(
                Code.Survey.ANSWER_RATING_OUT_OF_RANGE,
                field=f"answers.{q.id}",
                label=q.label,
            )
    except ValueError:
        raise_validation(
            Code.Survey.ANSWER_RATING_OUT_OF_RANGE,
            field=f"answers.{q.id}",
            label=q.label,
        )


def _validate_datetime_poll_answer(answer: dict[str, str], q: SurveyQuestion) -> None:
    """Validate a datetime poll answer (option -> "yes"|"maybe")."""
    valid_options = set(q.options or [])
    for option, availability in answer.items():
        if option not in valid_options:
            raise_validation(
                Code.Survey.ANSWER_INVALID_DATETIME_OPTION,
                field=f"answers.{q.id}",
                label=q.label,
            )
        if availability not in PollAvailability.VALID:
            raise_validation(
                Code.Survey.ANSWER_INVALID_AVAILABILITY,
                field=f"answers.{q.id}",
                label=q.label,
                value=availability,
            )


_TEXT_VALIDATORS: dict[str, Callable[[str, SurveyQuestion], None]] = {
    SurveyQuestionType.RADIO: _validate_choice_answer,
    SurveyQuestionType.SELECT: _validate_choice_answer,
    SurveyQuestionType.NUMBER: _validate_number_answer,
    SurveyQuestionType.BOOLEAN: _validate_boolean_answer,
    SurveyQuestionType.RATING: _validate_rating_answer,
}

_DICT_VALIDATORS: dict[str, Callable[[dict[str, str], SurveyQuestion], None]] = {
    SurveyQuestionType.DATETIME_POLL: _validate_datetime_poll_answer,
}


def _validate_one_answer(answer: str | list[str] | dict[str, str], q: SurveyQuestion) -> None:
    if q.field_type == SurveyQuestionType.CHECKBOX and isinstance(answer, str | list):
        _validate_checkbox_answer(answer, q)
        return
    if q.field_type in _DICT_VALIDATORS:
        if not isinstance(answer, dict):
            raise_validation(
                Code.Survey.ANSWER_INVALID_FORMAT,
                field=f"answers.{q.id}",
                label=q.label,
            )
        _DICT_VALIDATORS[q.field_type](answer, q)
        return
    if not isinstance(answer, str):
        raise_validation(
            Code.Survey.ANSWER_INVALID_FORMAT,
            field=f"answers.{q.id}",
            label=q.label,
        )
    validator = _TEXT_VALIDATORS.get(q.field_type)
    if validator is not None:
        validator(answer, q)


def _answerable_ids(
    questions: dict[str, SurveyQuestion], answers: dict[str, str | dict[str, str]]
) -> set[str]:
    visible = visible_question_ids(questions, answers)
    return {q_id for q_id in visible if questions[q_id].field_type != SurveyQuestionType.SECTION}


def _validate_survey_answers(
    answers: dict[str, str | list[str] | dict[str, str]],
    questions: dict[str, SurveyQuestion],
) -> None:
    """Raise ValidationException if any answer fails validation."""
    answerable = _answerable_ids(questions, answers)
    for q_id, q in questions.items():
        if q_id not in answerable:
            continue
        answer = answers.get(q_id)
        if answer is None or is_answer_empty(answer):
            if q.required:
                raise_validation(
                    Code.Survey.ANSWER_REQUIRED,
                    field=f"answers.{q_id}",
                    label=q.label,
                )
            continue
        _validate_one_answer(answer, q)


def _build_survey_answers(
    answers: dict[str, str | list[str] | dict[str, str]],
    questions: dict[str, SurveyQuestion],
) -> dict:
    result = {}
    answerable = _answerable_ids(questions, answers)
    for q_id, q in questions.items():
        if q_id not in answerable:
            continue
        answer = answers.get(q_id)
        if answer is None or is_answer_empty(answer):
            continue
        if isinstance(answer, list):
            answer = list(dict.fromkeys(checkbox_values(answer)))
        result[q_id] = {"label": q.label, "answer": answer}
    return result
