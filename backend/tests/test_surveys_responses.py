import json
from datetime import UTC, datetime

import pytest
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def admin_headers(db):
    user = User.objects.create_user(
        phone_number="+12025557020", password="x", first_name="Surveys", last_name="Admin"
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def survey(db):
    return Survey.objects.create(title="Feedback", slug="feedback")


def _patch(client, url, payload, headers):
    return client.patch(url, data=json.dumps(payload), content_type="application/json", **headers)


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

    def test_admin_can_delete_response(self, api_client, admin_headers, survey_with_response):
        survey, response = survey_with_response
        resp = api_client.delete(self._url(survey.id, response.id), **admin_headers)
        assert resp.status_code == 204
        assert not SurveyResponse.objects.filter(id=response.id).exists()

    def test_denied_without_permission(self, api_client, auth_headers, survey_with_response):
        survey, response = survey_with_response
        resp = api_client.delete(self._url(survey.id, response.id), **auth_headers)
        assert resp.status_code == 403
        assert_error_code(resp, Code.Perm.DENIED)
        assert SurveyResponse.objects.filter(id=response.id).exists()

    def test_404_for_response_from_another_survey(
        self, api_client, admin_headers, survey_with_response
    ):
        _, response = survey_with_response
        other_survey = Survey.objects.create(title="Other", slug="other-survey-1466")
        resp = api_client.delete(self._url(other_survey.id, response.id), **admin_headers)
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.RESPONSE_NOT_FOUND)
        assert SurveyResponse.objects.filter(id=response.id).exists()

    def test_404_for_missing_response(self, api_client, admin_headers, survey_with_response):
        survey, _ = survey_with_response
        resp = api_client.delete(
            self._url(survey.id, "00000000-0000-0000-0000-000000000000"),
            **admin_headers,
        )
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.RESPONSE_NOT_FOUND)


# ---------------------------------------------------------------------------
# Response listing must not attribute an anonymous survey (Issue 1466)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListSurveyResponsesAnonymity:
    def _url(self, survey_id):
        return f"/api/community/surveys/{survey_id}/responses/"

    def test_lists_responder_on_a_normal_survey(self, api_client, admin_headers, test_user):
        survey = Survey.objects.create(title="Named", slug="named-1466")
        SurveyResponse.objects.create(survey=survey, user=test_user, answers={})
        resp = api_client.get(self._url(survey.id), **admin_headers)
        assert resp.status_code == 200
        row = resp.json()[0]
        assert row["user_id"] == str(test_user.pk)
        assert row["user_name"]

    def test_masks_identities_collected_before_the_anonymous_flip(
        self, api_client, admin_headers, test_user
    ):
        survey = Survey.objects.create(title="Was named", slug="flipped-1466")
        SurveyResponse.objects.create(survey=survey, user=test_user, answers={})
        survey.anonymous = True
        survey.save(update_fields=["anonymous"])

        resp = api_client.get(self._url(survey.id), **admin_headers)
        assert resp.status_code == 200
        row = resp.json()[0]
        assert row["user_id"] is None
        assert row["user_name"] is None

    def test_anonymous_submitted_at_is_day_only(self, api_client, admin_headers):
        survey = Survey.objects.create(title="Anon", slug="anon-day-1466", anonymous=True)
        r = SurveyResponse.objects.create(survey=survey, answers={})
        SurveyResponse.objects.filter(id=r.id).update(
            submitted_at=datetime(2026, 3, 4, 15, 27, 11, tzinfo=UTC)
        )
        resp = api_client.get(self._url(survey.id), **admin_headers)
        assert resp.status_code == 200
        submitted = datetime.fromisoformat(resp.json()[0]["submitted_at"])
        assert submitted == datetime(2026, 3, 4, tzinfo=UTC)


@pytest.mark.django_db
class TestAnonymousToggleLock:
    def _url(self, survey_id):
        return f"/api/community/surveys/{survey_id}/"

    def test_can_toggle_before_any_responses(self, api_client, admin_headers, survey):
        resp = _patch(api_client, self._url(survey.id), {"anonymous": True}, admin_headers)
        assert resp.status_code == 200
        survey.refresh_from_db()
        assert survey.anonymous is True

    @pytest.mark.parametrize("start", [True, False])
    def test_cannot_toggle_once_responses_exist(self, api_client, admin_headers, survey, start):
        survey.anonymous = start
        survey.save(update_fields=["anonymous"])
        SurveyResponse.objects.create(survey=survey, answers={})
        resp = _patch(api_client, self._url(survey.id), {"anonymous": not start}, admin_headers)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.ANONYMOUS_LOCKED)
        survey.refresh_from_db()
        assert survey.anonymous is start

    def test_resending_the_same_value_is_allowed(self, api_client, admin_headers, survey):
        SurveyResponse.objects.create(survey=survey, answers={})
        resp = _patch(
            api_client, self._url(survey.id), {"anonymous": False, "title": "x"}, admin_headers
        )
        assert resp.status_code == 200
