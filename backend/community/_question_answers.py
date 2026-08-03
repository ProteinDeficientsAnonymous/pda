"""Shared answer validation helpers for join, survey, and RSVP questions."""

from collections.abc import Sequence

from community._validation import raise_validation


def is_answer_empty(answer: str | dict | None) -> bool:
    if answer is None:
        return True
    if isinstance(answer, dict):
        return len(answer) == 0
    return not str(answer).strip()


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


def assert_multiselect_members(
    answer: str,
    options: Sequence[str] | None,
    *,
    code: str,
    field: str,
    label: str,
) -> None:
    option_set = set(options or [])
    for val in answer.split(","):
        cleaned = val.strip()
        if cleaned and cleaned not in option_set:
            raise_validation(code, field=field, label=label)


def normalize_multiselect_csv(
    answer: str,
    options: Sequence[str] | None,
    *,
    code: str,
    field: str,
    label: str,
) -> str:
    cleaned = [v.strip() for v in str(answer).split(",") if v.strip()]
    option_set = set(options or [])
    for val in cleaned:
        if val not in option_set:
            raise_validation(code, field=field, label=label)
    return ",".join(cleaned)
