import json

import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def survey(db):
    survey = Survey.objects.create(title="Potluck ideas", slug="potluck-ideas")
    SurveyQuestion.objects.create(
        survey=survey, label="Thoughts?", field_type=SurveyQuestionType.TEXT
    )
    return survey


@pytest.fixture
def survey_manager(db):
    user = User.objects.create_user(phone_number="+12025558001", password="x", first_name="Sam")
    role = Role.objects.create(name="survey_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    user.roles.add(role)
    return user


def _headers(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


def _submit(api_client, survey, text="hi", **headers):
    question = survey.questions.first()
    return api_client.post(
        f"/api/community/surveys/view/{survey.slug}/respond/",
        data=json.dumps({"answers": {str(question.id): text}}),
        content_type="application/json",
        **headers,
    )


def _survey_notes():
    return Notification.objects.filter(notification_type=NotificationType.SURVEY_RESPONSE)


@pytest.mark.django_db
class TestSurveyResponseNotifications:
    def test_new_response_notifies_survey_managers(
        self, api_client, survey, survey_manager, auth_headers
    ):
        assert _submit(api_client, survey, **auth_headers).status_code == 201
        note = _survey_notes().get()
        assert note.recipient_id == survey_manager.id
        assert note.survey_id == survey.id
        assert note.message == "new response to Potluck ideas"
        assert note.related_user_id is None

    def test_submitter_with_manage_surveys_is_not_notified(
        self, api_client, survey, survey_manager
    ):
        _submit(api_client, survey, **_headers(survey_manager))
        assert not _survey_notes().exists()

    def test_updating_existing_response_does_not_notify(
        self, api_client, survey, survey_manager, auth_headers
    ):
        survey.one_response_per_user = True
        survey.save()
        _submit(api_client, survey, "first", **auth_headers)
        assert _submit(api_client, survey, "second", **auth_headers).status_code == 200
        assert _survey_notes().count() == 1

    def test_anonymous_response_notifies_without_naming_responder(
        self, api_client, survey, survey_manager
    ):
        assert _submit(api_client, survey).status_code == 201
        note = _survey_notes().get()
        assert note.related_user_id is None

    def test_list_exposes_survey_id(self, api_client, survey, survey_manager):
        _submit(api_client, survey)
        resp = api_client.get("/api/notifications/", **_headers(survey_manager))
        assert resp.json()[0]["survey_id"] == str(survey.id)
