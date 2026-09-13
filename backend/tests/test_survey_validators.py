"""Unit tests for survey answer validators (no DB)."""

from uuid import uuid4

import pytest
from community._survey_validators import (
    _build_survey_answers,
    _validate_boolean_answer,
    _validate_checkbox_answer,
    _validate_choice_answer,
    _validate_datetime_poll_answer,
    _validate_number_answer,
    _validate_one_answer,
    _validate_rating_answer,
    _validate_survey_answers,
)
from community._validation import Code, ValidationException
from community.models import SurveyQuestion, SurveyQuestionType

SLOT_A = "2030-01-01T18:00:00+00:00"
SLOT_B = "2030-01-02T18:00:00+00:00"


def make_question(field_type, options=None, required=False, label="q"):
    return SurveyQuestion(
        id=uuid4(),
        label=label,
        field_type=field_type,
        options=options or [],
        required=required,
    )


def assert_raises(code, fn, *args):
    with pytest.raises(ValidationException) as exc_info:
        fn(*args)
    assert exc_info.value.code == code
    return exc_info.value


class TestChoiceAnswer:
    def test_accepts_member(self):
        _validate_choice_answer("b", make_question(SurveyQuestionType.RADIO, ["a", "b"]))

    def test_rejects_non_member(self):
        q = make_question(SurveyQuestionType.SELECT, ["a", "b"], label="Pick")
        exc = assert_raises(Code.Survey.ANSWER_INVALID_OPTION, _validate_choice_answer, "z", q)
        assert exc.field == f"answers.{q.id}"
        assert exc.params == {"label": "Pick"}

    def test_rejects_when_no_options(self):
        q = make_question(SurveyQuestionType.RADIO, None)
        assert_raises(Code.Survey.ANSWER_INVALID_OPTION, _validate_choice_answer, "a", q)


class TestCheckboxAnswer:
    def test_accepts_csv_subset_with_whitespace(self):
        q = make_question(SurveyQuestionType.CHECKBOX, ["a", "b", "c"])
        _validate_checkbox_answer("a, c", q)

    def test_accepts_empty_string(self):
        _validate_checkbox_answer("", make_question(SurveyQuestionType.CHECKBOX, ["a"]))

    def test_rejects_any_non_member(self):
        q = make_question(SurveyQuestionType.CHECKBOX, ["a", "b"])
        assert_raises(Code.Survey.ANSWER_INVALID_OPTION, _validate_checkbox_answer, "a,z", q)


class TestNumberAnswer:
    @pytest.mark.parametrize("value", ["1", "-2.5", "1e3"])
    def test_accepts_numeric_strings(self, value):
        _validate_number_answer(value, make_question(SurveyQuestionType.NUMBER))

    def test_rejects_non_numeric(self):
        q = make_question(SurveyQuestionType.NUMBER)
        assert_raises(Code.Survey.ANSWER_MUST_BE_NUMBER, _validate_number_answer, "ten", q)


class TestBooleanAnswer:
    @pytest.mark.parametrize("value", ["yes", "no"])
    def test_accepts_yes_no(self, value):
        _validate_boolean_answer(value, make_question(SurveyQuestionType.BOOLEAN))

    @pytest.mark.parametrize("value", ["true", "Yes", "y", ""])
    def test_rejects_other_values(self, value):
        q = make_question(SurveyQuestionType.BOOLEAN)
        assert_raises(Code.Survey.ANSWER_MUST_BE_BOOLEAN, _validate_boolean_answer, value, q)


class TestRatingAnswer:
    @pytest.mark.parametrize("value", ["1", "3", "5"])
    def test_accepts_one_to_five(self, value):
        _validate_rating_answer(value, make_question(SurveyQuestionType.RATING))

    @pytest.mark.parametrize("value", ["0", "6", "-1", "3.5", "great"])
    def test_rejects_out_of_range_or_non_integer(self, value):
        q = make_question(SurveyQuestionType.RATING)
        assert_raises(Code.Survey.ANSWER_RATING_OUT_OF_RANGE, _validate_rating_answer, value, q)


class TestDatetimePollAnswer:
    def test_accepts_known_options_with_valid_availability(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A, SLOT_B])
        _validate_datetime_poll_answer({SLOT_A: "yes", SLOT_B: "maybe"}, q)

    def test_accepts_empty_dict(self):
        _validate_datetime_poll_answer({}, make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A]))

    def test_rejects_unknown_option(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A])
        assert_raises(
            Code.Survey.ANSWER_INVALID_DATETIME_OPTION,
            _validate_datetime_poll_answer,
            {SLOT_B: "yes"},
            q,
        )

    def test_rejects_invalid_availability(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A], label="When")
        exc = assert_raises(
            Code.Survey.ANSWER_INVALID_AVAILABILITY,
            _validate_datetime_poll_answer,
            {SLOT_A: "definitely"},
            q,
        )
        assert exc.params == {"label": "When", "value": "definitely"}


class TestOneAnswer:
    def test_dict_answer_for_text_question_is_format_error(self):
        q = make_question(SurveyQuestionType.TEXT)
        assert_raises(Code.Survey.ANSWER_INVALID_FORMAT, _validate_one_answer, {"a": "yes"}, q)

    def test_string_answer_for_poll_question_is_format_error(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A])
        assert_raises(Code.Survey.ANSWER_INVALID_FORMAT, _validate_one_answer, SLOT_A, q)

    @pytest.mark.parametrize("field_type", [SurveyQuestionType.TEXT, SurveyQuestionType.TEXTAREA])
    def test_free_text_accepts_anything(self, field_type):
        _validate_one_answer("anything goes", make_question(field_type))

    def test_dispatches_to_typed_validator(self):
        q = make_question(SurveyQuestionType.RATING)
        assert_raises(Code.Survey.ANSWER_RATING_OUT_OF_RANGE, _validate_one_answer, "9", q)

    def test_dispatches_to_dict_validator(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A])
        assert_raises(
            Code.Survey.ANSWER_INVALID_DATETIME_OPTION, _validate_one_answer, {SLOT_B: "yes"}, q
        )


class TestSurveyAnswers:
    def test_required_question_missing_raises(self):
        q = make_question(SurveyQuestionType.TEXT, required=True, label="Name")
        exc = assert_raises(Code.Survey.ANSWER_REQUIRED, _validate_survey_answers, {}, {str(q.id): q})
        assert exc.field == f"answers.{q.id}"
        assert exc.params == {"label": "Name"}

    @pytest.mark.parametrize("empty", ["", "   "])
    def test_required_question_blank_raises(self, empty):
        q = make_question(SurveyQuestionType.TEXT, required=True)
        assert_raises(
            Code.Survey.ANSWER_REQUIRED, _validate_survey_answers, {str(q.id): empty}, {str(q.id): q}
        )

    def test_required_poll_empty_dict_raises(self):
        q = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A], required=True)
        assert_raises(
            Code.Survey.ANSWER_REQUIRED, _validate_survey_answers, {str(q.id): {}}, {str(q.id): q}
        )

    def test_optional_question_may_be_skipped(self):
        q = make_question(SurveyQuestionType.NUMBER)
        _validate_survey_answers({}, {str(q.id): q})
        _validate_survey_answers({str(q.id): ""}, {str(q.id): q})

    def test_present_answers_are_validated(self):
        q = make_question(SurveyQuestionType.NUMBER)
        assert_raises(
            Code.Survey.ANSWER_MUST_BE_NUMBER,
            _validate_survey_answers,
            {str(q.id): "nope"},
            {str(q.id): q},
        )

    def test_unknown_question_ids_are_ignored(self):
        q = make_question(SurveyQuestionType.TEXT)
        _validate_survey_answers({"not-a-question": "x"}, {str(q.id): q})


class TestBuildSurveyAnswers:
    def test_labels_answers_and_drops_empties_and_unknowns(self):
        text = make_question(SurveyQuestionType.TEXT, label="Name")
        poll = make_question(SurveyQuestionType.DATETIME_POLL, [SLOT_A], label="When")
        skipped = make_question(SurveyQuestionType.TEXT, label="Skip")
        questions = {str(q.id): q for q in (text, poll, skipped)}
        answers = {
            str(text.id): "Ada",
            str(poll.id): {SLOT_A: "yes"},
            str(skipped.id): "  ",
            "unknown": "ignored",
        }
        assert _build_survey_answers(answers, questions) == {
            str(text.id): {"label": "Name", "answer": "Ada"},
            str(poll.id): {"label": "When", "answer": {SLOT_A: "yes"}},
        }

    def test_empty_input_builds_empty_dict(self):
        q = make_question(SurveyQuestionType.TEXT)
        assert _build_survey_answers({}, {str(q.id): q}) == {}
