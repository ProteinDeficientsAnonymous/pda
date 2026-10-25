from collections.abc import Sequence

from community._validation import raise_validation


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
