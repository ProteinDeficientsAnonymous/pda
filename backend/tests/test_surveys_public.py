"""Tests for public survey endpoints: tally authorization + submit rate limit."""

import json

import pytest
from audit.models import AuditLogEntry
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def survey_owner(db):
    return User.objects.create_user(
        phone_number="+12025557001",
        password="ownerpass",
        first_name="Survey",
        last_name="Owner",
    )


@pytest.fixture
def survey_owner_headers(survey_owner):
    refresh = RefreshToken.for_user(survey_owner)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def poll_survey(db, survey_owner):
    survey = Survey.objects.create(
        title="When should we meet?",
        slug="when-meet",
        created_by=survey_owner,
    )
    question = SurveyQuestion.objects.create(
        survey=survey,
        label="Pick a time",
        field_type=SurveyQuestionType.DATETIME_POLL,
        options=[future_iso(days=10), future_iso(days=11)],
    )
    SurveyResponse.objects.create(
        survey=survey,
        user=survey_owner,
        answers={str(question.id): {"answer": {future_iso(days=10): "yes"}}},
    )
    return survey


# ---------------------------------------------------------------------------
# Tally authorization (Issue 452 — IDOR voter enumeration)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSurveyTalliesAuthz:
    def _url(self, survey):
        return f"/api/community/surveys/{survey.id}/tallies/"

    def test_owner_can_read_tallies(self, api_client, survey_owner_headers, poll_survey):
        response = api_client.get(self._url(poll_survey), **survey_owner_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_manage_surveys_can_read_tallies(self, api_client, db, poll_survey):
        admin = User.objects.create_user(
            phone_number="+12025557010", password="x", first_name="Surveys", last_name="Admin"
        )
        role = Role.objects.create(name="surveys_mgr", permissions=[PermissionKey.MANAGE_SURVEYS])
        admin.roles.add(role)
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(admin).access_token}"  # type: ignore
        }
        response = api_client.get(self._url(poll_survey), **headers)
        assert response.status_code == 200

    def test_other_member_cannot_read_tallies(self, api_client, auth_headers, poll_survey):
        # A plain authenticated member must not enumerate voter names by UUID.
        response = api_client.get(self._url(poll_survey), **auth_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_unauthenticated_cannot_read_tallies(self, api_client, poll_survey):
        response = api_client.get(self._url(poll_survey))
        assert response.status_code == 401

    def test_missing_survey_404(self, api_client, survey_owner_headers):
        response = api_client.get(
            "/api/community/surveys/00000000-0000-0000-0000-000000000000/tallies/",
            **survey_owner_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Public survey submit rate limit (Issue 457)
# ---------------------------------------------------------------------------


@pytest.fixture
def public_text_survey(db):
    survey = Survey.objects.create(title="Public feedback", slug="public-feedback")
    SurveyQuestion.objects.create(
        survey=survey,
        label="Thoughts?",
        field_type=SurveyQuestionType.TEXT,
    )
    return survey


@pytest.mark.django_db
class TestSurveySubmitRateLimit:
    def test_submit_rate_limited(self, api_client, public_text_survey):
        question = public_text_survey.questions.first()
        url = f"/api/community/surveys/view/{public_text_survey.slug}/respond/"
        payload = json.dumps({"answers": {str(question.id): "looks good"}})

        last_status = None
        for _ in range(25):
            resp = api_client.post(url, data=payload, content_type="application/json")
            last_status = resp.status_code
            if last_status == 429:
                break

        assert last_status == 429, "expected the public survey submit to hit the rate limit"


# ---------------------------------------------------------------------------
# Anonymous surveys (Issue 1466)
# ---------------------------------------------------------------------------


@pytest.fixture
def anonymous_survey(db):
    survey = Survey.objects.create(
        title="Anonymous feedback",
        slug="anon-feedback",
        anonymous=True,
        one_response_per_user=True,
    )
    SurveyQuestion.objects.create(
        survey=survey,
        label="Thoughts?",
        field_type=SurveyQuestionType.TEXT,
    )
    return survey


@pytest.mark.django_db
class TestAnonymousSurveySubmit:
    def test_authenticated_submit_stores_no_user(self, api_client, auth_headers, anonymous_survey):
        question = anonymous_survey.questions.first()
        url = f"/api/community/surveys/view/{anonymous_survey.slug}/respond/"
        response = api_client.post(
            url,
            data=json.dumps({"answers": {str(question.id): "great"}}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["user_id"] is None
        stored = SurveyResponse.objects.get(survey=anonymous_survey)
        assert stored.user_id is None

    def test_submit_leaves_no_attributed_audit_row(
        self, api_client, auth_headers, anonymous_survey, django_capture_on_commit_callbacks
    ):
        question = anonymous_survey.questions.first()
        url = f"/api/community/surveys/view/{anonymous_survey.slug}/respond/"
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                url,
                data=json.dumps({"answers": {str(question.id): "great"}}),
                content_type="application/json",
                **auth_headers,
            )
        assert response.status_code == 201
        entry = AuditLogEntry.objects.get(action="survey_response_submitted")
        assert entry.actor_id is None
        assert entry.actor_label == "anonymous"
        assert entry.ip_address is None

    def test_non_anonymous_submit_still_records_the_actor(
        self,
        api_client,
        auth_headers,
        test_user,
        public_text_survey,
        django_capture_on_commit_callbacks,
    ):
        question = public_text_survey.questions.first()
        url = f"/api/community/surveys/view/{public_text_survey.slug}/respond/"
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                url,
                data=json.dumps({"answers": {str(question.id): "great"}}),
                content_type="application/json",
                **auth_headers,
            )
        assert response.status_code == 201
        entry = AuditLogEntry.objects.get(action="survey_response_submitted")
        assert entry.actor_id == test_user.pk

    def test_one_response_per_user_does_not_dedupe_anonymous(
        self, api_client, auth_headers, anonymous_survey
    ):
        # anonymous=True disables the one-per-user upsert since there's no
        # user to key it on — every submit creates a new response.
        question = anonymous_survey.questions.first()
        url = f"/api/community/surveys/view/{anonymous_survey.slug}/respond/"
        for _ in range(2):
            response = api_client.post(
                url,
                data=json.dumps({"answers": {str(question.id): "great"}}),
                content_type="application/json",
                **auth_headers,
            )
            assert response.status_code == 201
        assert SurveyResponse.objects.filter(survey=anonymous_survey).count() == 2

    def test_get_survey_public_omits_my_response_for_anonymous(
        self, api_client, auth_headers, anonymous_survey
    ):
        SurveyResponse.objects.create(survey=anonymous_survey, user=None, answers={})
        url = f"/api/community/surveys/view/{anonymous_survey.slug}/"
        response = api_client.get(url, **auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["my_response_id"] is None
        assert body["my_answers"] is None
