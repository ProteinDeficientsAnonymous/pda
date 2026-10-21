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


def _headers_for(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


@pytest.fixture
def surveys_admin_headers(db):
    admin = User.objects.create_user(
        phone_number="+12025557020", password="x", first_name="Surveys", last_name="Manager"
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    admin.roles.add(role)
    return _headers_for(admin)


@pytest.fixture
def events_admin_headers(db):
    host = User.objects.create_user(
        phone_number="+12025557021", password="x", first_name="Events", last_name="Manager"
    )
    role = Role.objects.create(name="events_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    host.roles.add(role)
    return _headers_for(host)


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

    def test_manage_events_can_still_read_tallies(
        self, api_client, events_admin_headers, poll_survey
    ):
        # Tallies keep the broader host-level rule that /summary/ no longer shares.
        response = api_client.get(self._url(poll_survey), **events_admin_headers)
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
# Per-question summaries (Issue 1462)
# ---------------------------------------------------------------------------

POLL_A = "2030-01-01T10:00:00+00:00"
POLL_B = "2030-01-02T10:00:00+00:00"


def _question(survey, label, field_type, options=None, order=0):
    return SurveyQuestion.objects.create(
        survey=survey,
        label=label,
        field_type=field_type,
        options=options or [],
        display_order=order,
    )


def _answers(pairs: dict) -> dict:
    return {str(q.id): {"label": q.label, "answer": value} for q, value in pairs.items()}


@pytest.fixture
def mixed_survey(db, survey_owner):
    survey = Survey.objects.create(title="Mixed", slug="mixed", created_by=survey_owner)
    radio = _question(survey, "Colour", SurveyQuestionType.RADIO, ["red", "blue"], 0)
    checkbox = _question(
        survey, "Toppings", SurveyQuestionType.CHECKBOX, ["tofu", "kale", "salsa"], 1
    )
    boolean = _question(survey, "Coming?", SurveyQuestionType.BOOLEAN, order=2)
    rating = _question(survey, "Vibes", SurveyQuestionType.RATING, order=3)
    text = _question(survey, "Notes", SurveyQuestionType.TEXT, order=4)
    poll = _question(survey, "When", SurveyQuestionType.DATETIME_POLL, [POLL_A, POLL_B], 5)
    SurveyResponse.objects.create(
        survey=survey,
        user=survey_owner,
        answers=_answers(
            {
                radio: "red",
                checkbox: "tofu,kale",
                boolean: "yes",
                rating: "5",
                text: "=SUM(A1)",
                poll: {POLL_B: "maybe", POLL_A: "yes"},
            }
        ),
    )
    SurveyResponse.objects.create(
        survey=survey,
        user=None,
        answers=_answers({radio: "blue", checkbox: "kale", boolean: "no", rating: "2"}),
    )
    SurveyResponse.objects.create(
        survey=survey,
        user=None,
        answers=_answers({radio: "red", checkbox: "", rating: ""}),
    )
    return survey


@pytest.mark.django_db
class TestSurveySummary:
    def _url(self, survey):
        return f"/api/community/surveys/{survey.id}/summary/"

    def _by_label(self, survey, body):
        label_by_id = {str(q.id): q.label for q in survey.questions.all()}
        return {label_by_id[row["question_id"]]: row for row in body}

    def test_counts_choice_boolean_and_rating(
        self, api_client, surveys_admin_headers, mixed_survey
    ):
        response = api_client.get(self._url(mixed_survey), **surveys_admin_headers)
        assert response.status_code == 200
        rows = self._by_label(mixed_survey, response.json())
        assert set(rows) == {"Colour", "Toppings", "Coming?", "Vibes"}

        assert rows["Colour"]["counts"] == {"red": 2, "blue": 1}
        assert rows["Colour"]["answered"] == 3
        assert rows["Colour"]["mean"] is None

        assert rows["Toppings"]["counts"] == {"tofu": 1, "kale": 2, "salsa": 0}
        assert rows["Toppings"]["answered"] == 2

        assert rows["Coming?"]["counts"] == {"yes": 1, "no": 1}
        assert rows["Coming?"]["answered"] == 2

        assert rows["Vibes"]["counts"] == {"1": 0, "2": 1, "3": 0, "4": 0, "5": 1}
        assert rows["Vibes"]["answered"] == 2
        assert rows["Vibes"]["mean"] == 3.5

    def test_rating_mean_is_none_without_answers(
        self, api_client, survey_owner, surveys_admin_headers
    ):
        survey = Survey.objects.create(title="Empty", slug="empty", created_by=survey_owner)
        _question(survey, "Vibes", SurveyQuestionType.RATING)
        response = api_client.get(self._url(survey), **surveys_admin_headers)
        assert response.status_code == 200
        assert response.json() == [
            {
                "question_id": str(survey.questions.get().id),
                "field_type": "rating",
                "counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "answered": 0,
                "mean": None,
            }
        ]

    def test_other_member_cannot_read_summary(self, api_client, auth_headers, mixed_survey):
        response = api_client.get(self._url(mixed_survey), **auth_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_manage_events_cannot_read_summary(
        self, api_client, events_admin_headers, mixed_survey
    ):
        response = api_client.get(self._url(mixed_survey), **events_admin_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_creator_without_manage_surveys_cannot_read_summary(
        self, api_client, survey_owner_headers, mixed_survey
    ):
        response = api_client.get(self._url(mixed_survey), **survey_owner_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_missing_survey_404_for_manage_surveys(self, api_client, surveys_admin_headers):
        response = api_client.get(
            "/api/community/surveys/00000000-0000-0000-0000-000000000000/summary/",
            **surveys_admin_headers,
        )
        assert response.status_code == 404

    def test_unauthenticated_cannot_read_summary(self, api_client, mixed_survey):
        assert api_client.get(self._url(mixed_survey)).status_code == 401

    def test_tallies_still_only_cover_datetime_polls(
        self, api_client, survey_owner_headers, mixed_survey
    ):
        response = api_client.get(
            f"/api/community/surveys/{mixed_survey.id}/tallies/", **survey_owner_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["tallies"] == {
            POLL_A: {"yes": 1, "maybe": 0},
            POLL_B: {"yes": 0, "maybe": 1},
        }


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
