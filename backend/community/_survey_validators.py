"""Answer validation logic for survey responses."""

from collections.abc import Callable

from community._validation import Code, raise_validation
from community.models import PollAvailability, SurveyQuestion, SurveyQuestionType


def _validate_choice_answer(answer: str, q: SurveyQuestion) -> None:
    if answer not in (q.options or []):
        raise_validation(
            Code.Survey.ANSWER_INVALID_OPTION,
            field=f"answers.{q.id}",
            label=q.label,
        )


def _validate_multiselect_answer(answer: str, q: SurveyQuestion) -> None:
    for val in answer.split(","):
        if val.strip() and val.strip() not in (q.options or []):
            raise_validation(
                Code.Survey.ANSWER_INVALID_OPTION,
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


def _validate_yes_no_answer(answer: str, q: SurveyQuestion) -> None:
    if answer not in ("yes", "no"):
        raise_validation(
            Code.Survey.ANSWER_MUST_BE_YES_NO,
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
    SurveyQuestionType.SELECT: _validate_choice_answer,
    SurveyQuestionType.DROPDOWN: _validate_choice_answer,
    SurveyQuestionType.MULTISELECT: _validate_multiselect_answer,
    SurveyQuestionType.NUMBER: _validate_number_answer,
    SurveyQuestionType.YES_NO: _validate_yes_no_answer,
    SurveyQuestionType.RATING: _validate_rating_answer,
}

_DICT_VALIDATORS: dict[str, Callable[[dict[str, str], SurveyQuestion], None]] = {
    SurveyQuestionType.DATETIME_POLL: _validate_datetime_poll_answer,
}


def _is_answer_empty(answer: str | dict) -> bool:
    if isinstance(answer, dict):
        return len(answer) == 0
    return not answer.strip()


def _validate_one_answer(answer: str | dict[str, str], q: SurveyQuestion) -> None:
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


def _validate_survey_answers(
    answers: dict[str, str | dict[str, str]],
    questions: dict[str, SurveyQuestion],
) -> None:
    """Raise ValidationException if any answer fails validation."""
    for q_id, q in questions.items():
        answer = answers.get(q_id)
        if answer is None or _is_answer_empty(answer):
            if q.required:
                raise_validation(
                    Code.Survey.ANSWER_REQUIRED,
                    field=f"answers.{q_id}",
                    label=q.label,
                )
            continue
        _validate_one_answer(answer, q)


def _build_survey_answers(
    answers: dict[str, str | dict[str, str]],
    questions: dict[str, SurveyQuestion],
) -> dict:
    result = {}
    for q_id, q in questions.items():
        answer = answers.get(q_id)
        if answer is None or _is_answer_empty(answer):
            continue
        result[q_id] = {"label": q.label, "answer": answer}
    return result
