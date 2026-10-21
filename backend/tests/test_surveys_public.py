"""Tests for public survey endpoints: tally authorization + submit rate limit."""

import json
from datetime import timedelta

import pytest
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
# Anonymous response token (Issue 1461)
# ---------------------------------------------------------------------------


@pytest.fixture
def one_per_user_survey(db):
    survey = Survey.objects.create(title="One each", slug="one-each", one_response_per_user=True)
    SurveyQuestion.objects.create(
        survey=survey, label="Thoughts?", field_type=SurveyQuestionType.TEXT
    )
    return survey


def _respond_url(survey):
    return f"/api/community/surveys/view/{survey.slug}/respond/"


def _view_url(survey):
    return f"/api/community/surveys/view/{survey.slug}/"


def _answers(survey, text):
    question = survey.questions.first()
    return json.dumps({"answers": {str(question.id): text}})


@pytest.mark.django_db
class TestAnonymousResponseToken:
    def test_first_anonymous_submit_issues_token(self, api_client, one_per_user_survey):
        resp = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "first"),
            content_type="application/json",
        )
        assert resp.status_code == 201
        token = resp.json()["response_token"]
        assert isinstance(token, str) and len(token) > 20
        assert SurveyResponse.objects.get(id=resp.json()["id"]).anonymous_token == token

    def test_resubmit_with_token_updates_in_place(self, api_client, one_per_user_survey):
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "first"),
            content_type="application/json",
        )
        token = first.json()["response_token"]
        second = api_client.post(
            _respond_url(one_per_user_survey) + f"?response_token={token}",
            data=_answers(one_per_user_survey, "second"),
            content_type="application/json",
        )
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert second.json()["response_token"] == token
        assert one_per_user_survey.responses.count() == 1
        question_id = str(one_per_user_survey.questions.first().id)
        assert one_per_user_survey.responses.get().answers[question_id]["answer"] == "second"

    def test_token_upsert_not_blocked_by_cap(self, api_client, one_per_user_survey):
        one_per_user_survey.max_responses = 1
        one_per_user_survey.save()
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "first"),
            content_type="application/json",
        )
        assert first.status_code == 201
        token = first.json()["response_token"]
        second = api_client.post(
            _respond_url(one_per_user_survey) + f"?response_token={token}",
            data=_answers(one_per_user_survey, "second"),
            content_type="application/json",
        )
        assert second.status_code == 200
        assert one_per_user_survey.responses.count() == 1
        fresh = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "someone else"),
            content_type="application/json",
        )
        assert fresh.status_code == 400
        assert_error_code(fresh, Code.Survey.CLOSED)

    def test_resubmit_without_token_creates_new_row(self, api_client, one_per_user_survey):
        for _ in range(2):
            resp = api_client.post(
                _respond_url(one_per_user_survey),
                data=_answers(one_per_user_survey, "again"),
                content_type="application/json",
            )
            assert resp.status_code == 201
        assert one_per_user_survey.responses.count() == 2

    def test_unknown_token_creates_new_row_with_fresh_token(self, api_client, one_per_user_survey):
        resp = api_client.post(
            _respond_url(one_per_user_survey) + "?response_token=not-a-real-token",
            data=_answers(one_per_user_survey, "hi"),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["response_token"] not in ("", None, "not-a-real-token")

    def test_get_with_token_returns_my_response(self, api_client, one_per_user_survey):
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "mine"),
            content_type="application/json",
        )
        token = first.json()["response_token"]
        with_token = api_client.get(_view_url(one_per_user_survey), {"response_token": token})
        assert with_token.status_code == 200
        assert with_token.json()["my_response_id"] == first.json()["id"]
        question_id = str(one_per_user_survey.questions.first().id)
        assert with_token.json()["my_answers"][question_id]["answer"] == "mine"

        without = api_client.get(_view_url(one_per_user_survey))
        assert without.json()["my_response_id"] is None
        assert without.json()["my_answers"] is None

    def test_no_token_when_multiple_responses_allowed(self, api_client, public_text_survey):
        resp = api_client.post(
            _respond_url(public_text_survey),
            data=_answers(public_text_survey, "free"),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["response_token"] is None
        assert SurveyResponse.objects.get(id=resp.json()["id"]).anonymous_token is None

    def test_authenticated_path_unchanged(self, api_client, auth_headers, one_per_user_survey):
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "first"),
            content_type="application/json",
            **auth_headers,
        )
        assert first.status_code == 201
        assert first.json()["response_token"] is None
        second = api_client.post(
            _respond_url(one_per_user_survey) + "?response_token=ignored",
            data=_answers(one_per_user_survey, "second"),
            content_type="application/json",
            **auth_headers,
        )
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert one_per_user_survey.responses.count() == 1
        assert one_per_user_survey.responses.get().anonymous_token is None

    def test_token_does_not_match_authenticated_rows(
        self, api_client, auth_headers, one_per_user_survey
    ):
        # A token-holding anonymous caller must never read or overwrite a member's row.
        api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "member"),
            content_type="application/json",
            **auth_headers,
        )
        member_row = one_per_user_survey.responses.get()
        member_row.anonymous_token = "leaked"
        member_row.save(update_fields=["anonymous_token"])
        resp = api_client.get(_view_url(one_per_user_survey), {"response_token": "leaked"})
        assert resp.json()["my_response_id"] is None

    def test_token_cannot_overwrite_a_members_row(
        self, api_client, auth_headers, one_per_user_survey
    ):
        # The write path must be scoped the same way the read path is.
        api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "member"),
            content_type="application/json",
            **auth_headers,
        )
        member_row = one_per_user_survey.responses.get()
        member_row.anonymous_token = "leaked"
        member_row.save(update_fields=["anonymous_token"])
        resp = api_client.post(
            _respond_url(one_per_user_survey) + "?response_token=leaked",
            data=_answers(one_per_user_survey, "hijacked"),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["id"] != str(member_row.id)
        member_row.refresh_from_db()
        question_id = str(one_per_user_survey.questions.first().id)
        assert member_row.answers[question_id]["answer"] == "member"

    def test_token_from_another_survey_does_not_match(self, api_client, one_per_user_survey):
        other = Survey.objects.create(
            title="Other", slug="other-one-each", one_response_per_user=True
        )
        SurveyQuestion.objects.create(survey=other, label="Q?", field_type=SurveyQuestionType.TEXT)
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "mine"),
            content_type="application/json",
        )
        token = first.json()["response_token"]
        view = api_client.get(_view_url(other), {"response_token": token})
        assert view.json()["my_response_id"] is None
        resp = api_client.post(
            _respond_url(other) + f"?response_token={token}",
            data=_answers(other, "elsewhere"),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.json()["response_token"] != token
        assert one_per_user_survey.responses.count() == 1

    def test_token_ignored_when_dedupe_is_disabled(self, api_client, one_per_user_survey):
        # Flipping one_response_per_user off must not leave a stale token able to
        # prefill a form whose submit path no longer reuses the row.
        first = api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "mine"),
            content_type="application/json",
        )
        token = first.json()["response_token"]
        one_per_user_survey.one_response_per_user = False
        one_per_user_survey.save(update_fields=["one_response_per_user"])
        view = api_client.get(_view_url(one_per_user_survey), {"response_token": token})
        assert view.json()["my_response_id"] is None
        assert view.json()["my_answers"] is None

    def test_oversized_token_is_not_queried(self, api_client, one_per_user_survey):
        oversized = "a" * 5000
        view = api_client.get(_view_url(one_per_user_survey), {"response_token": oversized})
        assert view.status_code == 200
        assert view.json()["my_response_id"] is None
        resp = api_client.post(
            _respond_url(one_per_user_survey) + f"?response_token={oversized}",
            data=_answers(one_per_user_survey, "hi"),
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_admin_listing_never_exposes_tokens(self, api_client, db, one_per_user_survey):
        admin = User.objects.create_user(
            phone_number="+12025557011", password="x", first_name="Surveys", last_name="Admin"
        )
        role = Role.objects.create(name="surveys_mgr2", permissions=[PermissionKey.MANAGE_SURVEYS])
        admin.roles.add(role)
        admin_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(admin).access_token}"  # type: ignore
        }
        api_client.post(
            _respond_url(one_per_user_survey),
            data=_answers(one_per_user_survey, "anon"),
            content_type="application/json",
        )
        url = f"/api/community/surveys/{one_per_user_survey.id}/responses/"
        listing = api_client.get(url, **admin_headers)
        assert listing.status_code == 200
        assert one_per_user_survey.responses.get().anonymous_token
        assert all("response_token" not in r for r in listing.json())
