import json

import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User


@pytest.fixture
def repeat_survey(db):
    survey = Survey.objects.create(title="Repeat", slug="repeat", one_response_per_user=False)
    SurveyQuestion.objects.create(survey=survey, label="Mood", field_type=SurveyQuestionType.TEXT)
    return survey


def _submit(api_client, survey, text, headers, response_id=None):
    question = survey.questions.first()
    url = f"/api/community/surveys/view/{survey.slug}/respond/"
    if response_id:
        url += f"?response_id={response_id}"
    payload = json.dumps({"answers": {str(question.id): text}})
    return api_client.post(url, data=payload, content_type="application/json", **headers)


def _answer(row, survey):
    return row.answers[str(survey.questions.first().id)]["answer"]


@pytest.mark.django_db
class TestMultiResponseEdit:
    def test_edit_updates_the_loaded_response(self, api_client, auth_headers, repeat_survey):
        first = _submit(api_client, repeat_survey, "great", auth_headers).json()
        edited = _submit(api_client, repeat_survey, "better", auth_headers, first["id"])
        assert edited.status_code == 200
        assert edited.json()["id"] == first["id"]
        row = SurveyResponse.objects.get(survey=repeat_survey)
        assert _answer(row, repeat_survey) == "better"

    def test_edit_leaves_the_users_other_responses_alone(
        self, api_client, auth_headers, repeat_survey
    ):
        first = _submit(api_client, repeat_survey, "one", auth_headers).json()
        second = _submit(api_client, repeat_survey, "two", auth_headers).json()
        _submit(api_client, repeat_survey, "one, edited", auth_headers, first["id"])
        assert SurveyResponse.objects.filter(survey=repeat_survey).count() == 2
        assert _answer(SurveyResponse.objects.get(id=first["id"]), repeat_survey) == "one, edited"
        assert _answer(SurveyResponse.objects.get(id=second["id"]), repeat_survey) == "two"

    def test_cannot_edit_another_members_response(self, api_client, auth_headers, repeat_survey):
        other = User.objects.create_user(phone_number="+12025557002", password="otherpass")
        other_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(other).access_token}"
        }  # type: ignore
        theirs = _submit(api_client, repeat_survey, "mine", other_headers).json()
        response = _submit(api_client, repeat_survey, "hijack", auth_headers, theirs["id"])
        assert response.status_code == 201
        assert response.json()["id"] != theirs["id"]
        assert _answer(SurveyResponse.objects.get(id=theirs["id"]), repeat_survey) == "mine"
