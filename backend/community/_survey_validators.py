"""Answer validation logic for survey responses."""

from collections.abc import Callable

from community.models import PollAvailability, SurveyQuestion, SurveyQuestionType


def _validate_choice_answer(answer: str, q: SurveyQuestion) -> str | None:
    if answer not in (q.options or []):
        return f'Invalid option for "{q.label}".'
    return None


def _validate_multiselect_answer(answer: str, q: SurveyQuestion) -> str | None:
    for val in answer.split(","):
        if val.strip() and val.strip() not in (q.options or []):
            return f'Invalid option for "{q.label}".'
    return None


def _validate_number_answer(answer: str, q: SurveyQuestion) -> str | None:
    try:
        float(answer)
    except ValueError:
        return f'"{q.label}" must be a number.'
    return None


def _validate_yes_no_answer(answer: str, q: SurveyQuestion) -> str | None:
    if answer not in ("yes", "no"):
        return f'"{q.label}" must be yes or no.'
    return None


def _validate_rating_answer(answer: str, q: SurveyQuestion) -> str | None:
    try:
        val = int(answer)
        if val < 1 or val > 5:
            return f'"{q.label}" must be between 1 and 5.'
    except ValueError:
        return f'"{q.label}" must be a number between 1 and 5.'
    return None


def _validate_datetime_poll_answer(
    answer: dict[str, str],
    q: SurveyQuestion,
) -> str | None:
    """Validate a datetime poll answer (option -> "yes"|"maybe")."""
    valid_options = set(q.options or [])
    for option, availability in answer.items():
        if option not in valid_options:
            return f'Invalid datetime option for "{q.label}".'
        if availability not in PollAvailability.VALID:
            return (
                f'Invalid availability "{availability}" for "{q.label}". Must be "yes" or "maybe".'
            )
    return None


_TEXT_VALIDATORS: dict[str, Callable[[str, SurveyQuestion], str | None]] = {
    SurveyQuestionType.SELECT: _validate_choice_answer,
    SurveyQuestionType.DROPDOWN: _validate_choice_answer,
    SurveyQuestionType.MULTISELECT: _validate_multiselect_answer,
    SurveyQuestionType.NUMBER: _validate_number_answer,
    SurveyQuestionType.YES_NO: _validate_yes_no_answer,
    SurveyQuestionType.RATING: _validate_rating_answer,
}

_DICT_VALIDATORS: dict[str, Callable[[dict[str, str], SurveyQuestion], str | None]] = {
    SurveyQuestionType.DATETIME_POLL: _validate_datetime_poll_answer,
}


def _is_answer_empty(answer: str | dict) -> bool:
    if isinstance(answer, dict):
        return len(answer) == 0
    return not answer.strip()


def _validate_one_answer(
    answer: str | dict[str, str],
    q: SurveyQuestion,
) -> str | None:
    if q.field_type in _DICT_VALIDATORS:
        if not isinstance(answer, dict):
            return f'Invalid answer format for "{q.label}".'
        return _DICT_VALIDATORS[q.field_type](answer, q)
    if not isinstance(answer, str):
        return f'Invalid answer format for "{q.label}".'
    return _TEXT_VALIDATORS.get(q.field_type, lambda a, _q: None)(answer, q)


def _validate_survey_answers(
    answers: dict[str, str | dict[str, str]],
    questions: dict[str, SurveyQuestion],
) -> str | None:
    for q_id, q in questions.items():
        answer = answers.get(q_id)
        if answer is None or _is_answer_empty(answer):
            if q.required:
                return f'"{q.label}" is required.'
            continue
        error = _validate_one_answer(answer, q)
        if error:
            return error
    return None


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
