import json
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso


@pytest.fixture
def public_text_survey(db):
    survey = Survey.objects.create(title="Feedback", slug="feedback", visibility="public")
    SurveyQuestion.objects.create(
        survey=survey, label="Thoughts?", field_type=SurveyQuestionType.TEXT
    )
    return survey


@pytest.fixture
def surveys_admin_headers(db):
    admin = User.objects.create_user(
        phone_number="+12025557020", password="x", first_name="Surveys", last_name="Admin"
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    admin.roles.add(role)
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(admin).access_token}"}  # type: ignore


def _view_url(survey):
    return f"/api/community/surveys/view/{survey.slug}/"


def _submit(api_client, survey, headers=None):
    question = survey.questions.first()
    return api_client.post(
        f"{_view_url(survey)}respond/",
        data=json.dumps({"answers": {str(question.id): "looks good"}}),
        content_type="application/json",
        **(headers or {}),
    )


@pytest.mark.django_db
class TestSurveyScheduling:
    # A survey outside its window or at cap still resolves on GET, so the UI can
    # tell a scheduled or capped survey apart from a closed one (Issue 1460).
    def test_before_opens_at_rejects_submits(self, api_client, public_text_survey):
        opens_at = timezone.now() + timedelta(hours=1)
        public_text_survey.opens_at = opens_at
        public_text_survey.save()
        view = api_client.get(_view_url(public_text_survey))
        assert view.status_code == 200
        assert view.json()["opens_at"] is not None
        resp = _submit(api_client, public_text_survey)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)

    def test_after_closes_at_rejects_submits(self, api_client, public_text_survey):
        public_text_survey.closes_at = timezone.now() - timedelta(minutes=1)
        public_text_survey.save()
        assert api_client.get(_view_url(public_text_survey)).status_code == 200
        resp = _submit(api_client, public_text_survey)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)

    def test_inside_window_is_open(self, api_client, public_text_survey):
        public_text_survey.opens_at = timezone.now() - timedelta(hours=1)
        public_text_survey.closes_at = timezone.now() + timedelta(hours=1)
        public_text_survey.save()
        assert api_client.get(_view_url(public_text_survey)).status_code == 200
        assert _submit(api_client, public_text_survey).status_code == 201

    def test_at_cap_rejects_submits(self, api_client, public_text_survey):
        public_text_survey.max_responses = 1
        public_text_survey.save()
        assert _submit(api_client, public_text_survey).status_code == 201
        resp = _submit(api_client, public_text_survey)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)
        view = api_client.get(_view_url(public_text_survey))
        assert view.status_code == 200
        assert view.json()["response_count"] == view.json()["max_responses"]

    def test_upsert_not_blocked_by_cap(self, api_client, auth_headers, public_text_survey):
        public_text_survey.one_response_per_user = True
        public_text_survey.max_responses = 1
        public_text_survey.save()
        assert _submit(api_client, public_text_survey, auth_headers).status_code == 201
        assert _submit(api_client, public_text_survey, auth_headers).status_code == 200
        assert public_text_survey.responses.count() == 1
        assert api_client.get(_view_url(public_text_survey), **auth_headers).status_code == 200

    def test_inactive_still_closed(self, api_client, public_text_survey):
        public_text_survey.is_active = False
        public_text_survey.save()
        resp = _submit(api_client, public_text_survey)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)


@pytest.mark.django_db
class TestSurveyScheduleAdmin:
    url = "/api/community/surveys/"

    def _create(self, api_client, headers, **extra):
        payload = {"title": "Scheduled", "slug": "scheduled", **extra}
        return api_client.post(
            self.url, data=json.dumps(payload), content_type="application/json", **headers
        )

    def test_create_with_schedule_and_cap(self, api_client, surveys_admin_headers):
        resp = self._create(
            api_client,
            surveys_admin_headers,
            opens_at=future_iso(days=1),
            closes_at=future_iso(days=2),
            max_responses=5,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["opens_at"] and body["closes_at"]
        assert body["max_responses"] == 5
        listed = api_client.get(f"{self.url}admin/", **surveys_admin_headers).json()
        assert listed[0]["max_responses"] == 5
        assert listed[0]["opens_at"] and listed[0]["closes_at"]

    def test_create_rejects_closes_before_opens(self, api_client, surveys_admin_headers):
        resp = self._create(
            api_client,
            surveys_admin_headers,
            opens_at=future_iso(days=2),
            closes_at=future_iso(days=1),
        )
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSES_BEFORE_OPENS)

    def test_create_rejects_zero_cap(self, api_client, surveys_admin_headers):
        assert self._create(api_client, surveys_admin_headers, max_responses=0).status_code == 422

    def test_patch_validates_against_stored_opens_at(self, api_client, surveys_admin_headers):
        survey = Survey.objects.create(
            title="S", slug="s", opens_at=timezone.now() + timedelta(days=2)
        )
        resp = api_client.patch(
            f"{self.url}{survey.id}/",
            data=json.dumps({"closes_at": future_iso(days=1)}),
            content_type="application/json",
            **surveys_admin_headers,
        )
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSES_BEFORE_OPENS)

    def test_patch_can_clear_fields(self, api_client, surveys_admin_headers):
        survey = Survey.objects.create(
            title="S",
            slug="s",
            opens_at=timezone.now(),
            closes_at=timezone.now() + timedelta(days=1),
            max_responses=3,
        )
        resp = api_client.patch(
            f"{self.url}{survey.id}/",
            data=json.dumps({"opens_at": None, "closes_at": None, "max_responses": None}),
            content_type="application/json",
            **surveys_admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["opens_at"] is None and body["closes_at"] is None
        assert body["max_responses"] is None
