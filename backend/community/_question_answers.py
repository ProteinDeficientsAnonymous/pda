from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from community.models import QuestionType
from community.validation import raise_validation

ChoiceAnswer = str | list[str]


class ChoiceQuestion(Protocol):
    @property
    def field_type(self) -> str: ...
    @property
    def options(self) -> Sequence[str] | None: ...
    @property
    def label(self) -> str: ...


@dataclass(frozen=True)
class AnswerCodes:
    invalid_option: str
    invalid_format: str


def is_answer_empty(answer: str | list | dict | None) -> bool:
    if answer is None:
        return True
    if isinstance(answer, list):
        return not checkbox_values(answer)
    if isinstance(answer, dict):
        return len(answer) == 0
    return not str(answer).strip()


def checkbox_values(answer: str | list[str]) -> list[str]:
    """Ticked options; a legacy comma-joined string is split on commas."""
    raw = answer if isinstance(answer, list) else str(answer).split(",")
    return [v.strip() for v in raw if v.strip()]


def assert_single_choice_member(
    answer: str,
    options: Sequence[str] | None,
    *,
    code: str,
    field: str,
    label: str,
) -> None:
    if answer not in (options or []):
        raise_validation(code, field=field, label=label)


def assert_checkbox_members(
    answer: str | list[str],
    options: Sequence[str] | None,
    *,
    code: str,
    field: str,
    label: str,
) -> None:
    option_set = set(options or [])
    for val in checkbox_values(answer):
        if val not in option_set:
            raise_validation(code, field=field, label=label)


def normalize_answer(
    answer: ChoiceAnswer, q: ChoiceQuestion, *, codes: AnswerCodes, field: str
) -> ChoiceAnswer:
    """Validate a text/select/checkbox answer; checkbox comes back as a deduped list."""
    invalid_option = {"code": codes.invalid_option, "field": field, "label": q.label}
    if q.field_type == QuestionType.CHECKBOX:
        assert_checkbox_members(answer, q.options, **invalid_option)
        return list(dict.fromkeys(checkbox_values(answer)))
    if isinstance(answer, list):
        raise_validation(codes.invalid_format, field=field, label=q.label)
    text = answer.strip()
    if q.field_type == QuestionType.SELECT and text:
        assert_single_choice_member(text, q.options, **invalid_option)
    return text
