"""Tests for public survey endpoints: tally authorization + submit rate limit."""

import json
import logging
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community._validation import Code
from community.models import (
    DatetimePollResult,
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
# One-response-per-user upsert
# ---------------------------------------------------------------------------


@pytest.fixture
def upsert_survey(db):
    survey = Survey.objects.create(title="Checkin", slug="checkin", one_response_per_user=True)
    SurveyQuestion.objects.create(survey=survey, label="Mood", field_type=SurveyQuestionType.TEXT)
    return survey


@pytest.mark.django_db
class TestSurveySubmitUpsert:
    def _submit(self, api_client, survey, text, headers=None):
        question = survey.questions.first()
        url = f"/api/community/surveys/view/{survey.slug}/respond/"
        payload = json.dumps({"answers": {str(question.id): text}})
        kwargs = {**headers} if headers else {}
        return api_client.post(url, data=payload, content_type="application/json", **kwargs)

    def test_first_submit_creates_response(self, api_client, auth_headers, upsert_survey):
        response = self._submit(api_client, upsert_survey, "great", auth_headers)
        assert response.status_code == 201
        assert SurveyResponse.objects.filter(survey=upsert_survey).count() == 1

    def test_second_submit_updates_in_place(self, api_client, auth_headers, upsert_survey):
        first = self._submit(api_client, upsert_survey, "great", auth_headers)
        second = self._submit(api_client, upsert_survey, "even better", auth_headers)
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert SurveyResponse.objects.filter(survey=upsert_survey).count() == 1
        row = SurveyResponse.objects.get(survey=upsert_survey)
        question = upsert_survey.questions.first()
        assert row.answers[str(question.id)]["answer"] == "even better"

    def test_off_creates_a_second_row_per_user(self, api_client, auth_headers, test_user):
        survey = Survey.objects.create(title="Repeat", slug="repeat", one_response_per_user=False)
        SurveyQuestion.objects.create(
            survey=survey, label="Mood", field_type=SurveyQuestionType.TEXT
        )
        first = self._submit(api_client, survey, "great", auth_headers)
        second = self._submit(api_client, survey, "still great", auth_headers)
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
        assert SurveyResponse.objects.filter(survey=survey).count() == 2

    def test_anonymous_submits_are_never_upserted(self, api_client, upsert_survey):
        first = self._submit(api_client, upsert_survey, "great")
        second = self._submit(api_client, upsert_survey, "also great")
        assert first.status_code == 201
        assert second.status_code == 201
        assert SurveyResponse.objects.filter(survey=upsert_survey).count() == 2


# ---------------------------------------------------------------------------
# Closed surveys (Issue 1460)
# ---------------------------------------------------------------------------


@pytest.fixture
def closed_survey(db):
    survey = Survey.objects.create(title="Closed feedback", slug="closed-feedback", is_active=False)
    SurveyQuestion.objects.create(
        survey=survey,
        label="Thoughts?",
        field_type=SurveyQuestionType.TEXT,
    )
    return survey


@pytest.fixture
def closed_members_survey(db):
    survey = Survey.objects.create(
        title="Closed members",
        slug="closed-members",
        description="Secret members-only debrief",
        is_active=False,
        visibility=SurveyVisibility.MEMBERS_ONLY,
    )
    SurveyQuestion.objects.create(
        survey=survey,
        label="Secret question?",
        field_type=SurveyQuestionType.TEXT,
    )
    return survey


@pytest.fixture
def finalized_poll_survey(db):
    survey = Survey.objects.create(title="Finalized poll", slug="finalized-poll", is_active=False)
    SurveyQuestion.objects.create(
        survey=survey,
        label="When works?",
        field_type=SurveyQuestionType.DATETIME_POLL,
        options=[future_iso()],
    )
    DatetimePollResult.objects.create(
        survey=survey, winning_datetime=timezone.now() + timedelta(days=30)
    )
    return survey


@pytest.mark.django_db
class TestClosedSurvey:
    def _view_url(self, survey):
        return f"/api/community/surveys/view/{survey.slug}/"

    def _respond_url(self, survey):
        return f"/api/community/surveys/view/{survey.slug}/respond/"

    def test_get_closed_survey_returns_inactive(self, api_client, closed_survey):
        resp = api_client.get(self._view_url(closed_survey))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["slug"] == closed_survey.slug

    def test_get_closed_members_survey_hidden_from_anonymous(
        self, api_client, closed_members_survey
    ):
        resp = api_client.get(self._view_url(closed_members_survey))
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.NOT_FOUND)
        body = resp.content.decode()
        assert closed_members_survey.title not in body
        assert closed_members_survey.description not in body
        assert "Secret question?" not in body

    def test_get_closed_members_survey_visible_to_member(
        self, api_client, auth_headers, closed_members_survey
    ):
        resp = api_client.get(self._view_url(closed_members_survey), **auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_submit_to_closed_survey_rejected(self, api_client, closed_survey):
        question = closed_survey.questions.first()
        payload = json.dumps({"answers": {str(question.id): "too late"}})
        resp = api_client.post(
            self._respond_url(closed_survey), data=payload, content_type="application/json"
        )
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)
        assert not SurveyResponse.objects.filter(survey=closed_survey).exists()

    def test_submit_to_closed_members_survey_hidden_from_anonymous(
        self, api_client, closed_members_survey
    ):
        resp = api_client.post(
            self._respond_url(closed_members_survey),
            data=json.dumps({"answers": {}}),
            content_type="application/json",
        )
        # NOT_FOUND must win over CLOSED here, or the 400 would confirm the survey exists.
        assert resp.status_code == 404
        assert_error_code(resp, Code.Survey.NOT_FOUND)

    def test_get_finalized_poll_is_readable(self, api_client, finalized_poll_survey):
        resp = api_client.get(self._view_url(finalized_poll_survey))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        assert data["poll_result"] is not None

    def test_submit_to_finalized_poll_rejected(self, api_client, finalized_poll_survey):
        resp = api_client.post(
            self._respond_url(finalized_poll_survey),
            data=json.dumps({"answers": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.CLOSED)
        assert not SurveyResponse.objects.filter(survey=finalized_poll_survey).exists()


# ---------------------------------------------------------------------------
# Anonymous surveys (Issue 1466)
# ---------------------------------------------------------------------------


@pytest.fixture
def middleware_caplog(caplog, monkeypatch):
    monkeypatch.setattr(logging.getLogger("pda"), "propagate", True)
    return caplog


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

    def test_request_log_line_drops_user_id(
        self, api_client, auth_headers, anonymous_survey, middleware_caplog
    ):
        question = anonymous_survey.questions.first()
        url = f"/api/community/surveys/view/{anonymous_survey.slug}/respond/"
        with middleware_caplog.at_level(logging.INFO, logger="pda.middleware"):
            response = api_client.post(
                url,
                data=json.dumps({"answers": {str(question.id): "great"}}),
                content_type="application/json",
                **auth_headers,
            )
        assert response.status_code == 201
        [record] = [r for r in middleware_caplog.records if r.name == "pda.middleware"]
        assert record.user_id is None  # type: ignore[attr-defined]

    def test_request_log_line_keeps_user_id_on_named_survey(
        self, api_client, auth_headers, test_user, public_text_survey, middleware_caplog
    ):
        question = public_text_survey.questions.first()
        url = f"/api/community/surveys/view/{public_text_survey.slug}/respond/"
        with middleware_caplog.at_level(logging.INFO, logger="pda.middleware"):
            response = api_client.post(
                url,
                data=json.dumps({"answers": {str(question.id): "great"}}),
                content_type="application/json",
                **auth_headers,
            )
        assert response.status_code == 201
        [record] = [r for r in middleware_caplog.records if r.name == "pda.middleware"]
        assert record.user_id == str(test_user.pk)  # type: ignore[attr-defined]

    def test_tallies_omit_voters(self, api_client, survey_owner_headers, poll_survey):
        poll_survey.anonymous = True
        poll_survey.save(update_fields=["anonymous"])
        response = api_client.get(
            f"/api/community/surveys/{poll_survey.id}/tallies/", **survey_owner_headers
        )
        assert response.status_code == 200
        [tally] = response.json()
        assert tally["total_responses"] == 1
        assert all(voters == [] for voters in tally["voters"].values())
