"""Tests for admin survey response deletion (Issue 1466)."""

import pytest
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def surveys_admin_user(db):
    user = User.objects.create_user(
        phone_number="+12025557020",
        password="adminpass123",
        first_name="Surveys",
        last_name="Admin",
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    user.roles.add(role)
    return user


@pytest.fixture
def surveys_admin_headers(surveys_admin_user):
    refresh = RefreshToken.for_user(surveys_admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def survey_with_response(db):
    survey = Survey.objects.create(title="Feedback", slug="feedback-1466")
    question = SurveyQuestion.objects.create(
        survey=survey,
        label="Thoughts?",
        field_type=SurveyQuestionType.TEXT,
    )
    response = SurveyResponse.objects.create(
        survey=survey,
        user=None,
        answers={str(question.id): {"answer": "nice"}},
    )
    return survey, response


@pytest.mark.django_db
class TestDeleteSurveyResponse:
    def _url(self, survey_id, response_id):
        return f"/api/community/surveys/{survey_id}/responses/{response_id}/"

    def test_admin_can_delete_response(
        self, api_client, surveys_admin_headers, survey_with_response
    ):
        survey, response = survey_with_response
        resp = api_client.delete(self._url(survey.id, response.id), **surveys_admin_headers)
        assert resp.status_code == 204
        assert not SurveyResponse.objects.filter(id=response.id).exists()

    def test_denied_without_permission(self, api_client, auth_headers, survey_with_response):
        survey, response = survey_with_response
        resp = api_client.delete(self._url(survey.id, response.id), **auth_headers)
        assert resp.status_code == 403
        assert_error_code(resp, Code.Perm.DENIED)
        assert SurveyResponse.objects.filter(id=response.id).exists()

    def test_404_for_response_from_another_survey(
        self, api_client, surveys_admin_headers, survey_with_response
    ):
        _, response = survey_with_response
        other_survey = Survey.objects.create(title="Other", slug="other-survey-1466")
        resp = api_client.delete(self._url(other_survey.id, response.id), **surveys_admin_headers)
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.RESPONSE_NOT_FOUND)
        assert SurveyResponse.objects.filter(id=response.id).exists()

    def test_404_for_missing_response(
        self, api_client, surveys_admin_headers, survey_with_response
    ):
        survey, _ = survey_with_response
        resp = api_client.delete(
            self._url(survey.id, "00000000-0000-0000-0000-000000000000"),
            **surveys_admin_headers,
        )
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.RESPONSE_NOT_FOUND)
