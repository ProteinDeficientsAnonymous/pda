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
