import json

import pytest
from community._validation import Code
from community.models import Survey, SurveyQuestionType
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._survey_condition_helpers import equals, make_question


@pytest.fixture
def admin_headers(db):
    admin = User.objects.create_user(
        phone_number="+12025557301", password="x", first_name="Sect", last_name="Admin"
    )
    role = Role.objects.create(name="section_mgr", permissions=[PermissionKey.MANAGE_SURVEYS])
    admin.roles.add(role)
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(admin).access_token}"}  # type: ignore


@pytest.fixture
def survey(db):
    return Survey.objects.create(title="Sections", slug="sections")


def _post(api_client, headers, survey, payload):
    return api_client.post(
        f"/api/community/surveys/{survey.id}/questions/",
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestSectionAuthoring:
    def test_create_section_keeps_description_and_drops_answer_fields(
        self, api_client, admin_headers, survey
    ):
        response = _post(
            api_client,
            admin_headers,
            survey,
            {
                "label": "about you",
                "field_type": SurveyQuestionType.SECTION,
                "description": "these are optional",
                "options": ["stray"],
                "required": True,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["description"] == "these are optional"
        assert body["options"] == []
        assert body["required"] is False

    def test_description_cleared_on_other_types(self, api_client, admin_headers, survey):
        q = make_question(survey, "about you", SurveyQuestionType.SECTION, description="optional")
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{q.id}/",
            data=json.dumps({"label": "name", "field_type": SurveyQuestionType.TEXT}),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        q.refresh_from_db()
        assert q.description == ""

    def test_section_can_be_conditional(self, api_client, admin_headers, survey):
        source = make_question(survey, "member?", SurveyQuestionType.BOOLEAN)
        response = _post(
            api_client,
            admin_headers,
            survey,
            {
                "label": "your involvement",
                "field_type": SurveyQuestionType.SECTION,
                "show_if": equals(source, "yes"),
            },
        )
        assert response.status_code == 201
        assert response.json()["show_if"]["question_id"] == str(source.id)

    def test_section_cannot_be_condition_source(self, api_client, admin_headers, survey):
        section = make_question(survey, "about you", SurveyQuestionType.SECTION)
        response = _post(
            api_client,
            admin_headers,
            survey,
            {"label": "age", "show_if": equals(section, "x")},
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_TYPE_NOT_SUPPORTED)
