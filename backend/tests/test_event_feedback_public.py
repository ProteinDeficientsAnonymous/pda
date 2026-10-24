import json
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import (
    Event,
    EventFeedbackRequest,
    EventType,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.utils import timezone

from tests._asserts import assert_error_code


@pytest.fixture
def feedback_survey(db):
    survey = Survey.objects.create(
        title="official feedback",
        slug="official-feedback",
        anonymous=True,
        feedback_event_type=EventType.OFFICIAL,
    )
    SurveyQuestion.objects.create(
        survey=survey, label="how was it?", field_type=SurveyQuestionType.TEXT, required=True
    )
    return survey


@pytest.fixture
def event(db, test_user):
    start = timezone.now() - timedelta(days=1)
    return Event.objects.create(
        title="vegan potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        created_by=test_user,
    )


@pytest.fixture
def feedback_request(event, test_user):
    return EventFeedbackRequest.objects.create(
        event=event, user=test_user, token=EventFeedbackRequest.new_token()
    )


def _answers(survey: Survey, text: str = "loved it") -> str:
    question = survey.questions.first()
    assert question is not None
    return json.dumps({"answers": {str(question.id): text}})


@pytest.mark.django_db
class TestFeedbackSurveySlugHidden:
    def test_feedback_survey_hidden_from_slug_view_and_respond(self, api_client, feedback_survey):
        view = api_client.get(f"/api/community/surveys/view/{feedback_survey.slug}/")
        assert view.status_code == 404
        assert_error_code(view, Code.Survey.NOT_FOUND)

        respond = api_client.post(
            f"/api/community/surveys/view/{feedback_survey.slug}/respond/",
            data=_answers(feedback_survey),
            content_type="application/json",
        )
        assert respond.status_code == 404
        assert_error_code(respond, Code.Survey.NOT_FOUND)
        assert not SurveyResponse.objects.filter(survey=feedback_survey).exists()


def _url(token: str) -> str:
    return f"/api/community/feedback/{token}/"


@pytest.mark.django_db
class TestGetFeedbackLink:
    def test_get_returns_survey_and_event_title(
        self, api_client, feedback_survey, feedback_request, event
    ):
        response = api_client.get(_url(feedback_request.token))
        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == str(event.id)
        assert body["event_title"] == "vegan potluck"
        assert body["event_start"] is not None
        assert body["already_responded"] is False
        assert body["is_open"] is True
        assert body["survey"]["id"] == str(feedback_survey.id)
        assert [q["label"] for q in body["survey"]["questions"]] == ["how was it?"]
        assert body["survey"]["my_response_id"] is None
        assert body["survey"]["my_answers"] is None

    def test_unknown_token_404(self, api_client, feedback_survey):
        response = api_client.get(_url("not-a-real-token"))
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.FEEDBACK_LINK_INVALID)

    def test_get_without_feedback_survey_returns_no_survey(self, api_client, feedback_request):
        response = api_client.get(_url(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["survey"] is None
        assert response.json()["is_open"] is False

    def test_get_after_survey_deactivated_reports_closed(
        self, api_client, feedback_survey, feedback_request
    ):
        feedback_survey.is_active = False
        feedback_survey.save(update_fields=["is_active"])
        response = api_client.get(_url(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["is_open"] is False

    def test_get_after_responding_reports_already_responded(
        self, api_client, feedback_survey, feedback_request
    ):
        feedback_request.responded_on = timezone.localdate()
        feedback_request.save(update_fields=["responded_on"])
        response = api_client.get(_url(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["already_responded"] is True
