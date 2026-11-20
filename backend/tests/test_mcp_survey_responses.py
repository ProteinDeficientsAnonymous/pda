import json
import uuid

import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from mcp.server.mcpserver.exceptions import ToolError
from users.helpers import visible_display_name

from tests._mcp_tool_helpers import run_tool, tool_names

pytestmark = pytest.mark.django_db


def _call(user, **arguments):
    return run_tool(user, "get_survey_responses", **arguments)


def _survey(**fields):
    survey = Survey.objects.create(title="feedback", slug="feedback", **fields)
    text = SurveyQuestion.objects.create(
        survey=survey, label="how was it", field_type=SurveyQuestionType.TEXT, display_order=0
    )
    SurveyQuestion.objects.create(
        survey=survey, label="part one", field_type=SurveyQuestionType.SECTION, display_order=1
    )
    rating = SurveyQuestion.objects.create(
        survey=survey, label="rating", field_type=SurveyQuestionType.NUMBER, display_order=2
    )
    return survey, text, rating


def _respond(survey, answers, user=None):
    return SurveyResponse.objects.create(
        survey=survey,
        user=user,
        answers={str(q.id): {"label": q.label, "answer": a} for q, a in answers.items()},
    )


def test_tool_needs_manage_surveys(test_user, surveys_admin):
    survey, *_ = _survey()
    assert "get_survey_responses" not in tool_names(test_user)
    assert "get_survey_responses" in tool_names(surveys_admin)
    with pytest.raises(ToolError, match="permission"):
        _call(test_user, survey=survey.slug)


def test_admin_gets_responses_grouped_per_question(surveys_admin, test_user):
    survey, text, rating = _survey()
    _respond(survey, {text: "great", rating: 5}, user=test_user)
    _respond(survey, {text: "meh"})
    body = _call(surveys_admin, survey=survey.slug)
    assert _call(surveys_admin, survey=str(survey.id)) == body
    assert body["survey"] == {
        "id": str(survey.id),
        "slug": "feedback",
        "title": "feedback",
        "anonymous": False,
    }
    assert (body["response_count"], body["next_offset"]) == (2, None)
    assert [q["label"] for q in body["questions"]] == ["how was it", "rating"]
    answers = body["questions"][0]["answers"]
    assert sorted(a["answer"] for a in answers) == ["great", "meh"]
    named = next(a for a in answers if a["answer"] == "great")
    assert named["respondent"] == visible_display_name(test_user, surveys_admin)
    assert [a["answer"] for a in body["questions"][1]["answers"]] == [5]


def test_anonymous_survey_hides_respondent_and_exact_time(surveys_admin, test_user):
    survey, text, _ = _survey(anonymous=True)
    _respond(survey, {text: "great"}, user=test_user)
    body = _call(surveys_admin, survey=survey.slug)
    (answer,) = body["questions"][0]["answers"]
    assert answer["answer"] == "great"
    assert "respondent" not in answer
    assert len(answer["submitted_at"]) == len("2026-11-07")
    assert str(test_user.id) not in json.dumps(body)
    assert visible_display_name(test_user, surveys_admin) not in json.dumps(body)


def test_responses_page(surveys_admin):
    survey, text, _ = _survey()
    for n in range(3):
        _respond(survey, {text: f"r{n}"})
    first = _call(surveys_admin, survey=survey.slug, limit=2)
    assert first["next_offset"] == 2
    assert len(first["questions"][0]["answers"]) == 2
    last = _call(surveys_admin, survey=survey.slug, limit=2, offset=2)
    assert (last["next_offset"], len(last["questions"][0]["answers"])) == (None, 1)


def test_unknown_survey(surveys_admin):
    with pytest.raises(ToolError, match="404"):
        _call(surveys_admin, survey=str(uuid.uuid4()))
