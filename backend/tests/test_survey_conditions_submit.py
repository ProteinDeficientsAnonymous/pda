"""Tests for conditional survey question visibility and submission."""

import json

import pytest
from community._survey_conditions import visible_question_ids
from community._validation import Code
from community.models import ShowIfOperator, Survey, SurveyQuestionType, SurveyResponse

from tests._asserts import assert_error_code
from tests._survey_condition_helpers import equals, make_question, not_equals


@pytest.fixture
def survey(db):
    return Survey.objects.create(title="Conditions", slug="conditions")


# ---------------------------------------------------------------------------
# Visibility evaluation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVisibleQuestionIds:
    def test_condition_met_and_unmet(self, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey, "Why?", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        questions = {str(source.id): source, str(dependent.id): dependent}

        assert visible_question_ids(questions, {str(source.id): "vegan"}) == set(questions)
        assert visible_question_ids(questions, {str(source.id): "veg"}) == {str(source.id)}

    def test_checkbox_contains(self, survey):
        source = make_question(
            survey, "Interests", SurveyQuestionType.CHECKBOX, options=["food", "art"], order=0
        )
        dependent = make_question(
            survey,
            "Favourite dish?",
            SurveyQuestionType.TEXT,
            order=1,
            show_if={
                "question_id": str(source.id),
                "operator": ShowIfOperator.CONTAINS.value,
                "value": "food",
            },
        )
        questions = {str(source.id): source, str(dependent.id): dependent}

        assert str(dependent.id) in visible_question_ids(questions, {str(source.id): "art,food"})
        assert str(dependent.id) not in visible_question_ids(questions, {str(source.id): "art"})

    def test_not_equals_on_single_choice(self, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey,
            "Why not?",
            SurveyQuestionType.TEXT,
            order=1,
            show_if=not_equals(source, "vegan"),
        )
        questions = {str(source.id): source, str(dependent.id): dependent}

        assert str(dependent.id) in visible_question_ids(questions, {str(source.id): "veg"})
        assert str(dependent.id) not in visible_question_ids(questions, {str(source.id): "vegan"})

    def test_checkbox_not_equals_means_not_ticked(self, survey):
        source = make_question(
            survey, "Interests", SurveyQuestionType.CHECKBOX, options=["food", "art"], order=0
        )
        dependent = make_question(
            survey,
            "Why not food?",
            SurveyQuestionType.TEXT,
            order=1,
            show_if=not_equals(source, "food"),
        )
        questions = {str(source.id): source, str(dependent.id): dependent}

        assert str(dependent.id) not in visible_question_ids(
            questions, {str(source.id): "food,art"}
        )
        assert str(dependent.id) in visible_question_ids(questions, {str(source.id): "art"})

    def test_checkbox_equals_matches_any_ticked_box(self, survey):
        source = make_question(
            survey, "Interests", SurveyQuestionType.CHECKBOX, options=["food", "art"], order=0
        )
        dependent = make_question(
            survey,
            "Favourite dish?",
            SurveyQuestionType.TEXT,
            order=1,
            show_if=equals(source, "food"),
        )
        questions = {str(source.id): source, str(dependent.id): dependent}

        assert str(dependent.id) in visible_question_ids(questions, {str(source.id): "art,food"})

    def test_hiding_cascades_down_a_chain(self, survey):
        first = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        second = make_question(
            survey,
            "Member?",
            SurveyQuestionType.BOOLEAN,
            order=1,
            show_if=equals(first, "vegan"),
        )
        third = make_question(
            survey, "Since when?", SurveyQuestionType.TEXT, order=2, show_if=equals(second, "yes")
        )
        questions = {str(q.id): q for q in (first, second, third)}

        answers = {str(first.id): "veg", str(second.id): "yes"}
        assert visible_question_ids(questions, answers) == {str(first.id)}


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSubmitWithConditions:
    def _submit(self, api_client, survey, answers):
        return api_client.post(
            f"/api/community/surveys/view/{survey.slug}/respond/",
            data=json.dumps({"answers": answers}),
            content_type="application/json",
        )

    def test_hidden_required_question_is_not_enforced(self, api_client, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        make_question(
            survey,
            "Why vegan?",
            SurveyQuestionType.TEXT,
            order=1,
            required=True,
            show_if=equals(source, "vegan"),
        )
        response = self._submit(api_client, survey, {str(source.id): "veg"})
        assert response.status_code == 201

    def test_visible_required_question_is_still_enforced(self, api_client, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey,
            "Why vegan?",
            SurveyQuestionType.TEXT,
            order=1,
            required=True,
            show_if=equals(source, "vegan"),
        )
        response = self._submit(api_client, survey, {str(source.id): "vegan"})
        assert response.status_code == 422
        assert_error_code(response, Code.Survey.ANSWER_REQUIRED, f"answers.{dependent.id}")

    def test_answers_to_hidden_questions_are_dropped(self, api_client, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey, "Why vegan?", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        response = self._submit(
            api_client, survey, {str(source.id): "veg", str(dependent.id): "smuggled"}
        )
        assert response.status_code == 201
        stored = SurveyResponse.objects.get(survey=survey).answers
        assert str(dependent.id) not in stored
        assert str(source.id) in stored

    def test_invalid_answer_to_hidden_question_is_ignored(self, api_client, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey,
            "How many years?",
            SurveyQuestionType.NUMBER,
            order=1,
            show_if=equals(source, "vegan"),
        )
        response = self._submit(
            api_client, survey, {str(source.id): "veg", str(dependent.id): "not a number"}
        )
        assert response.status_code == 201
        assert str(dependent.id) not in SurveyResponse.objects.get(survey=survey).answers
