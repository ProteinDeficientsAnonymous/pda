from types import SimpleNamespace

import pytest
from community._question_answers import (
    AnswerCodes,
    assert_checkbox_members,
    assert_single_choice_member,
    is_answer_empty,
    normalize_answer,
)
from community.models import QuestionType
from community.validation import ValidationException

CODES = AnswerCodes(invalid_option="bad_option", invalid_format="bad_format")


def _normalize(answer, field_type):
    q = SimpleNamespace(field_type=field_type, options=["a", "b"], label="q")
    return normalize_answer(answer, q, codes=CODES, field="f")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("x", False),
        ({}, True),
        ({"a": "yes"}, False),
    ],
)
def test_is_answer_empty_scenarios(answer, expected):
    assert is_answer_empty(answer) is expected


@pytest.mark.unit
def test_assert_single_choice_member_rejects_unknown_option():
    with pytest.raises(ValidationException) as exc_info:
        assert_single_choice_member(
            "nope",
            ["a", "b"],
            code="test.invalid_option",
            field="answers.1",
            label="Meal",
        )
    assert exc_info.value.code == "test.invalid_option"
    assert exc_info.value.field == "answers.1"


@pytest.mark.unit
def test_assert_single_choice_member_accepts_known_option():
    assert_single_choice_member(
        "a",
        ["a", "b"],
        code="test.invalid_option",
        field="answers.1",
        label="Meal",
    )


@pytest.mark.unit
def test_assert_checkbox_members_rejects_unknown_option():
    with pytest.raises(ValidationException) as exc_info:
        assert_checkbox_members(
            "a, nope",
            ["a", "b"],
            code="test.invalid_option",
            field="answers.1",
            label="Tags",
        )
    assert exc_info.value.code == "test.invalid_option"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("answer", "field_type", "expected"),
    [
        (["a", "b", "a"], QuestionType.CHECKBOX, ["a", "b"]),
        ("a, b", QuestionType.CHECKBOX, ["a", "b"]),
        ("  a ", QuestionType.SELECT, "a"),
        ("", QuestionType.SELECT, ""),
        (" hi ", QuestionType.TEXT, "hi"),
    ],
)
def test_normalize_answer_scenarios(answer, field_type, expected):
    assert _normalize(answer, field_type) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("answer", "field_type", "code"),
    [
        (["a", "z"], QuestionType.CHECKBOX, "bad_option"),
        ("z", QuestionType.SELECT, "bad_option"),
        (["a"], QuestionType.TEXT, "bad_format"),
    ],
)
def test_normalize_answer_rejects(answer, field_type, code):
    with pytest.raises(ValidationException) as exc_info:
        _normalize(answer, field_type)
    assert exc_info.value.code == code
