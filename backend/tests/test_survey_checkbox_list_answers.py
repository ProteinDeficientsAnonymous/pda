import json

import pytest
from community._question_answers import checkbox_values
from community._survey_conditions import visible_question_ids
from community._survey_reports import _csv_answer_cell, _summarize_question
from community._validation import Code
from community.models import ShowIfOperator, Survey, SurveyQuestionType, SurveyResponse

from tests._asserts import assert_error_code
from tests._survey_condition_helpers import make_question

CLUBS = "club events (book club, movie club)"


@pytest.fixture
def survey(db):
    return Survey.objects.create(title="Interests", slug="interests")


@pytest.fixture
def interests(survey):
    return make_question(
        survey, "Interests", SurveyQuestionType.CHECKBOX, options=[CLUBS, "potlucks"], order=0
    )


def _submit(api_client, survey, answers):
    return api_client.post(
        f"/api/community/surveys/view/{survey.slug}/respond/",
        data=json.dumps({"answers": answers}),
        content_type="application/json",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ([" a, b ", "", "c"], ["a, b", "c"]),
        ("a, b,,", ["a", "b"]),
    ],
)
def test_checkbox_values_keeps_list_items_whole_and_splits_legacy_strings(answer, expected):
    assert checkbox_values(answer) == expected


@pytest.mark.django_db
class TestCheckboxListAnswers:
    def test_option_with_comma_submits_and_is_stored_as_list(self, api_client, survey, interests):
        response = _submit(api_client, survey, {str(interests.id): [CLUBS, CLUBS, "potlucks"]})
        assert response.status_code == 201
        stored = SurveyResponse.objects.get(survey=survey).answers[str(interests.id)]
        assert stored["answer"] == [CLUBS, "potlucks"]

    def test_unknown_option_in_list_is_rejected(self, api_client, survey, interests):
        response = _submit(api_client, survey, {str(interests.id): ["nope"]})
        assert response.status_code == 422
        assert_error_code(response, Code.Survey.ANSWER_INVALID_OPTION, f"answers.{interests.id}")

    def test_empty_list_counts_as_unanswered(self, api_client, survey, interests):
        interests.required = True
        interests.save()
        response = _submit(api_client, survey, {str(interests.id): []})
        assert response.status_code == 422
        assert_error_code(response, Code.Survey.ANSWER_REQUIRED, f"answers.{interests.id}")

    def test_list_answer_to_single_choice_question_is_rejected(self, api_client, survey):
        radio = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=1)
        response = _submit(api_client, survey, {str(radio.id): ["vegan"]})
        assert response.status_code == 422
        assert_error_code(response, Code.Survey.ANSWER_INVALID_FORMAT, f"answers.{radio.id}")

    def test_contains_condition_matches_option_with_comma(self, survey, interests):
        dependent = make_question(
            survey,
            "Which club?",
            SurveyQuestionType.TEXT,
            order=1,
            show_if={
                "question_id": str(interests.id),
                "operator": ShowIfOperator.CONTAINS.value,
                "value": CLUBS,
            },
        )
        questions = {str(interests.id): interests, str(dependent.id): dependent}
        assert str(dependent.id) in visible_question_ids(questions, {str(interests.id): [CLUBS]})
        assert str(dependent.id) not in visible_question_ids(
            questions, {str(interests.id): ["potlucks"]}
        )

    def test_summary_and_csv_keep_option_with_comma_whole(self, survey, interests):
        answer = [CLUBS, "potlucks"]
        response = SurveyResponse.objects.create(
            survey=survey, answers={str(interests.id): {"label": "Interests", "answer": answer}}
        )
        summary = _summarize_question(interests, [response])
        assert summary.counts == {CLUBS: 1, "potlucks": 1}
        assert summary.answered == 1
        assert _csv_answer_cell(interests, answer) == f"{CLUBS}\npotlucks"
