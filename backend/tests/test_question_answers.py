import pytest
from community._question_answers import (
    assert_checkbox_members,
    assert_single_choice_member,
    is_answer_empty,
    normalize_checkbox_csv,
)
from community._validation import ValidationException


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
def test_normalize_checkbox_csv_strips_and_joins():
    assert (
        normalize_checkbox_csv(
            " a , b , ",
            ["a", "b"],
            code="test.invalid_option",
            field="answers.1",
            label="Tags",
        )
        == "a,b"
    )
