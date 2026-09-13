"""Tests for admin survey endpoints: CRUD, questions, reorder, responses, permissions."""

import json
import logging
from unittest.mock import MagicMock

import pytest
from community import _surveys
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code

JSON = "application/json"
MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def surveys_admin(db):
    user = User.objects.create_user(
        phone_number="+12025557100", password="x", first_name="Surveys", last_name="Admin"
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    user.roles.add(role)
    return user


@pytest.fixture
def admin_headers(surveys_admin):
    refresh = RefreshToken.for_user(surveys_admin)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def survey(db, surveys_admin):
    survey = Survey.objects.create(title="Feedback", slug="feedback", created_by=surveys_admin)
    SurveyQuestion.objects.create(
        survey=survey, label="First", field_type=SurveyQuestionType.TEXT, display_order=0
    )
    SurveyQuestion.objects.create(
        survey=survey,
        label="Second",
        field_type=SurveyQuestionType.RADIO,
        options=["a", "b"],
        display_order=1,
    )
    return survey


@pytest.fixture
def audit_spy(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(_surveys, "audit_log", spy)
    return spy


def _post(client, url, payload, headers):
    return client.post(url, data=json.dumps(payload), content_type=JSON, **headers)


def _patch(client, url, payload, headers):
    return client.patch(url, data=json.dumps(payload), content_type=JSON, **headers)


def _put(client, url, payload, headers):
    return client.put(url, data=json.dumps(payload), content_type=JSON, **headers)


@pytest.mark.django_db
class TestListSurveysAdmin:
    def test_lists_surveys_with_response_count(self, api_client, admin_headers, survey):
        SurveyResponse.objects.create(survey=survey, answers={})
        response = api_client.get("/api/community/surveys/admin/", **admin_headers)
        assert response.status_code == 200
        [row] = response.json()
        assert row["id"] == str(survey.id)
        assert row["slug"] == "feedback"
        assert row["response_count"] == 1

    def test_unauthenticated_401(self, api_client):
        assert api_client.get("/api/community/surveys/admin/").status_code == 401


@pytest.mark.django_db
class TestCreateSurvey:
    def test_creates_survey(self, api_client, admin_headers, surveys_admin):
        payload = {
            "title": "New survey",
            "description": "tell us things",
            "slug": "new-survey",
            "visibility": "members_only",
            "is_active": False,
            "one_response_per_user": True,
        }
        response = _post(api_client, "/api/community/surveys/", payload, admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "new-survey"
        assert data["visibility"] == "members_only"
        assert data["is_active"] is False
        assert data["one_response_per_user"] is True
        assert data["questions"] == []
        assert data["created_by_id"] == str(surveys_admin.id)
        assert Survey.objects.get(slug="new-survey").created_by == surveys_admin

    def test_duplicate_slug_400(self, api_client, admin_headers, survey):
        response = _post(
            api_client,
            "/api/community/surveys/",
            {"title": "Dup", "slug": survey.slug},
            admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.SLUG_ALREADY_EXISTS, "slug")
        assert Survey.objects.filter(slug=survey.slug).count() == 1

    def test_unknown_linked_event_400(self, api_client, admin_headers):
        response = _post(
            api_client,
            "/api/community/surveys/",
            {"title": "Linked", "slug": "linked", "linked_event_id": MISSING_ID},
            admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.NOT_FOUND, "linked_event_id")
        assert not Survey.objects.filter(slug="linked").exists()


@pytest.mark.django_db
class TestGetSurveyAdmin:
    def test_returns_survey_with_questions(self, api_client, admin_headers, survey):
        response = api_client.get(f"/api/community/surveys/{survey.id}/admin/", **admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(survey.id)
        assert [q["label"] for q in data["questions"]] == ["First", "Second"]

    def test_missing_404(self, api_client, admin_headers):
        response = api_client.get(f"/api/community/surveys/{MISSING_ID}/admin/", **admin_headers)
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.NOT_FOUND)


@pytest.mark.django_db
class TestUpdateSurvey:
    def test_patches_only_sent_fields(self, api_client, admin_headers, survey):
        response = _patch(
            api_client,
            f"/api/community/surveys/{survey.id}/",
            {"title": "Renamed", "is_active": False},
            admin_headers,
        )
        assert response.status_code == 200
        survey.refresh_from_db()
        assert survey.title == "Renamed"
        assert survey.is_active is False
        assert survey.slug == "feedback"
        assert response.json()["questions"][0]["label"] == "First"

    def test_slug_collision_400(self, api_client, admin_headers, survey):
        Survey.objects.create(title="Other", slug="taken")
        response = _patch(
            api_client, f"/api/community/surveys/{survey.id}/", {"slug": "taken"}, admin_headers
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.SLUG_ALREADY_EXISTS, "slug")
        survey.refresh_from_db()
        assert survey.slug == "feedback"

    def test_same_slug_is_not_a_collision(self, api_client, admin_headers, survey):
        response = _patch(
            api_client,
            f"/api/community/surveys/{survey.id}/",
            {"slug": survey.slug},
            admin_headers,
        )
        assert response.status_code == 200

    def test_missing_404(self, api_client, admin_headers):
        response = _patch(
            api_client, f"/api/community/surveys/{MISSING_ID}/", {"title": "x"}, admin_headers
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeleteSurvey:
    def test_deletes_survey_and_questions(self, api_client, admin_headers, survey):
        response = api_client.delete(f"/api/community/surveys/{survey.id}/", **admin_headers)
        assert response.status_code == 204
        assert not Survey.objects.filter(id=survey.id).exists()
        assert not SurveyQuestion.objects.filter(survey_id=survey.id).exists()

    def test_missing_404(self, api_client, admin_headers):
        response = api_client.delete(f"/api/community/surveys/{MISSING_ID}/", **admin_headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestSurveyQuestions:
    def test_create_appends_at_end(self, api_client, admin_headers, survey):
        response = _post(
            api_client,
            f"/api/community/surveys/{survey.id}/questions/",
            {"label": "Third", "field_type": "checkbox", "options": ["x", "y"], "required": True},
            admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_order"] == 2
        assert data["field_type"] == "checkbox"
        assert data["options"] == ["x", "y"]
        assert data["required"] is True
        assert survey.questions.count() == 3

    def test_create_on_missing_survey_404(self, api_client, admin_headers):
        response = _post(
            api_client,
            f"/api/community/surveys/{MISSING_ID}/questions/",
            {"label": "x"},
            admin_headers,
        )
        assert response.status_code == 404

    def test_update_replaces_all_fields(self, api_client, admin_headers, survey):
        q = survey.questions.get(label="Second")
        response = _patch(
            api_client,
            f"/api/community/surveys/{survey.id}/questions/{q.id}/",
            {"label": "Second!", "field_type": "select", "options": ["c"], "required": True},
            admin_headers,
        )
        assert response.status_code == 200
        q.refresh_from_db()
        assert q.label == "Second!"
        assert q.field_type == SurveyQuestionType.SELECT
        assert q.options == ["c"]
        assert q.required is True

    def test_update_scoped_to_survey_404(self, api_client, admin_headers, survey):
        other = Survey.objects.create(title="Other", slug="other")
        q = survey.questions.first()
        response = _patch(
            api_client,
            f"/api/community/surveys/{other.id}/questions/{q.id}/",
            {"label": "hijack"},
            admin_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.QUESTION_NOT_FOUND)
        q.refresh_from_db()
        assert q.label == "First"

    def test_delete_question(self, api_client, admin_headers, survey):
        q = survey.questions.first()
        response = api_client.delete(
            f"/api/community/surveys/{survey.id}/questions/{q.id}/", **admin_headers
        )
        assert response.status_code == 204
        assert not SurveyQuestion.objects.filter(id=q.id).exists()
        assert survey.questions.count() == 1

    def test_delete_missing_question_404(self, api_client, admin_headers, survey):
        response = api_client.delete(
            f"/api/community/surveys/{survey.id}/questions/{MISSING_ID}/", **admin_headers
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.QUESTION_NOT_FOUND)


@pytest.mark.django_db
class TestReorderSurveyQuestions:
    def test_reorders_by_position_in_payload(self, api_client, admin_headers, survey):
        first, second = list(survey.questions.all())
        response = _put(
            api_client,
            f"/api/community/surveys/{survey.id}/questions/order/",
            {"question_ids": [str(second.id), str(first.id)]},
            admin_headers,
        )
        assert response.status_code == 200
        assert [q["label"] for q in response.json()] == ["Second", "First"]
        first.refresh_from_db()
        second.refresh_from_db()
        assert (second.display_order, first.display_order) == (0, 1)

    def test_ignores_questions_from_other_surveys(self, api_client, admin_headers, survey):
        other = Survey.objects.create(title="Other", slug="other")
        foreign = SurveyQuestion.objects.create(
            survey=other, label="Foreign", field_type=SurveyQuestionType.TEXT, display_order=5
        )
        response = _put(
            api_client,
            f"/api/community/surveys/{survey.id}/questions/order/",
            {"question_ids": [str(foreign.id)]},
            admin_headers,
        )
        assert response.status_code == 200
        foreign.refresh_from_db()
        assert foreign.display_order == 5

    def test_missing_survey_404(self, api_client, admin_headers):
        response = _put(
            api_client,
            f"/api/community/surveys/{MISSING_ID}/questions/order/",
            {"question_ids": []},
            admin_headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestListSurveyResponses:
    def test_lists_member_and_anonymous_responses(
        self, api_client, admin_headers, survey, test_user
    ):
        member_row = SurveyResponse.objects.create(
            survey=survey, user=test_user, answers={"q": {"label": "First", "answer": "hi"}}
        )
        anon_row = SurveyResponse.objects.create(survey=survey, answers={})
        response = api_client.get(f"/api/community/surveys/{survey.id}/responses/", **admin_headers)
        assert response.status_code == 200
        by_id = {r["id"]: r for r in response.json()}
        assert set(by_id) == {str(member_row.id), str(anon_row.id)}
        assert by_id[str(member_row.id)]["user_id"] == str(test_user.id)
        assert "Test" in by_id[str(member_row.id)]["user_name"]
        assert by_id[str(member_row.id)]["answers"] == {"q": {"label": "First", "answer": "hi"}}
        assert by_id[str(anon_row.id)]["user_id"] is None
        assert by_id[str(anon_row.id)]["user_name"] is None

    def test_missing_survey_404(self, api_client, admin_headers):
        response = api_client.get(
            f"/api/community/surveys/{MISSING_ID}/responses/", **admin_headers
        )
        assert response.status_code == 404


def _denied_calls(survey_id, question_id):
    base = f"/api/community/surveys/{survey_id}"
    return [
        ("list_surveys_admin", "get", "/api/community/surveys/admin/", None),
        ("create_survey", "post", "/api/community/surveys/", {"title": "x", "slug": "x"}),
        ("get_survey_admin", "get", f"{base}/admin/", None),
        ("update_survey", "patch", f"{base}/", {"title": "x"}),
        ("delete_survey", "delete", f"{base}/", None),
        ("create_survey_question", "post", f"{base}/questions/", {"label": "x"}),
        ("update_survey_question", "patch", f"{base}/questions/{question_id}/", {"label": "x"}),
        ("delete_survey_question", "delete", f"{base}/questions/{question_id}/", None),
        ("reorder_survey_questions", "put", f"{base}/questions/order/", {"question_ids": []}),
        ("list_survey_responses", "get", f"{base}/responses/", None),
    ]


@pytest.mark.django_db
class TestManageSurveysPermission:
    @pytest.mark.parametrize("index", range(10))
    def test_plain_member_denied_and_audited(
        self, api_client, auth_headers, survey, audit_spy, index
    ):
        question = survey.questions.first()
        endpoint, method, url, payload = _denied_calls(survey.id, question.id)[index]
        kwargs = {**auth_headers}
        if payload is not None:
            kwargs.update(data=json.dumps(payload), content_type=JSON)
        response = getattr(api_client, method)(url, **kwargs)

        assert response.status_code == 403, endpoint
        assert_error_code(response, Code.Perm.DENIED)
        audit_spy.assert_called_once()
        args, kwargs = audit_spy.call_args
        assert args[:2] == (logging.WARNING, "permission_denied")
        assert kwargs["persist"] is False
        details = kwargs["target"].details
        assert details["endpoint"] == endpoint
        assert details["required_permission"] == PermissionKey.MANAGE_SURVEYS

    def test_denied_member_makes_no_changes(self, api_client, auth_headers, survey):
        _post(api_client, "/api/community/surveys/", {"title": "x", "slug": "sneaky"}, auth_headers)
        api_client.delete(f"/api/community/surveys/{survey.id}/", **auth_headers)
        assert not Survey.objects.filter(slug="sneaky").exists()
        assert Survey.objects.filter(id=survey.id).exists()
