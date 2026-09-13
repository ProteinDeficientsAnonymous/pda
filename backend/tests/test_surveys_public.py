"""Tests for public survey endpoints: list visibility, tally authorization, submit rate limit."""

import json
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import (
    Event,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
    SurveyVisibility,
)
from django.utils import timezone
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
# Public survey list visibility (Issue 1463)
# ---------------------------------------------------------------------------


@pytest.fixture
def discoverable_surveys(db):
    public = Survey.objects.create(title="Public survey", slug="public-survey")
    members_only = Survey.objects.create(
        title="Members survey",
        slug="members-survey",
        visibility=SurveyVisibility.MEMBERS_ONLY,
    )
    Survey.objects.create(title="Closed survey", slug="closed-survey", is_active=False)
    Survey.objects.create(
        title="Closed members survey",
        slug="closed-members-survey",
        visibility=SurveyVisibility.MEMBERS_ONLY,
        is_active=False,
    )
    return public, members_only


@pytest.mark.django_db
class TestSurveyListPublic:
    url = "/api/community/surveys/"

    def test_anonymous_sees_only_public_active(self, api_client, discoverable_surveys):
        response = api_client.get(self.url)
        assert response.status_code == 200
        assert [s["slug"] for s in response.json()] == ["public-survey"]

    def test_member_sees_members_only(self, api_client, auth_headers, discoverable_surveys):
        response = api_client.get(self.url, **auth_headers)
        assert response.status_code == 200
        assert sorted(s["slug"] for s in response.json()) == ["members-survey", "public-survey"]

    def test_inactive_surveys_excluded_for_members(
        self, api_client, auth_headers, discoverable_surveys
    ):
        slugs = {s["slug"] for s in api_client.get(self.url, **auth_headers).json()}
        assert "closed-survey" not in slugs
        assert "closed-members-survey" not in slugs

    def test_includes_linked_event_id(self, api_client, db):
        event = Event.objects.create(
            title="Potluck", start_datetime=timezone.now() + timedelta(days=7)
        )
        Survey.objects.create(title="Potluck poll", slug="potluck-poll", linked_event=event)

        body = api_client.get(self.url).json()

        assert body[0]["linked_event_id"] == str(event.id)
        assert body[0]["title"] == "Potluck poll"
