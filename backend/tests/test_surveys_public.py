"""Tests for public survey endpoints: tally authorization + submit rate limit."""

import json
from datetime import timedelta

import pytest
from community._event_helpers import _event_out
from community._validation import Code
from community.models import (
    DatetimePollResult,
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
# Open/close scheduling + response cap (Issue 1465)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Event survey links respect scheduling + cap, not just is_active (Issue 1465)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEventSurveyLinkVisibility:
    def _event(self):
        return Event.objects.create(
            title="Potluck", start_datetime=timezone.now() + timedelta(days=10)
        )

    def test_scheduled_survey_excluded_from_links(self):
        event = self._event()
        Survey.objects.create(
            title="Feedback",
            slug="scheduled-feedback",
            linked_event=event,
            opens_at=timezone.now() + timedelta(hours=1),
        )
        assert _event_out(event).linked_surveys == []

    def test_closed_survey_excluded_from_links(self):
        event = self._event()
        Survey.objects.create(
            title="Feedback",
            slug="closed-feedback",
            linked_event=event,
            closes_at=timezone.now() - timedelta(minutes=1),
        )
        assert _event_out(event).linked_surveys == []

    def test_at_cap_survey_excluded_from_links(self):
        event = self._event()
        survey = Survey.objects.create(
            title="Feedback", slug="capped-feedback", linked_event=event, max_responses=1
        )
        SurveyResponse.objects.create(survey=survey)
        assert _event_out(event).linked_surveys == []

    def test_open_survey_included_in_links(self):
        event = self._event()
        Survey.objects.create(title="Feedback", slug="open-feedback", linked_event=event)
        assert [s.slug for s in _event_out(event).linked_surveys] == ["open-feedback"]

    def test_scheduled_poll_excluded_from_datetime_poll_slug(self):
        event = self._event()
        survey = Survey.objects.create(
            title="When?",
            slug="when-poll",
            linked_event=event,
            opens_at=timezone.now() + timedelta(hours=1),
        )
        SurveyQuestion.objects.create(
            survey=survey,
            label="Pick a time",
            field_type=SurveyQuestionType.DATETIME_POLL,
            options=[future_iso(days=10)],
        )
        assert _event_out(event).datetime_poll_slug is None
