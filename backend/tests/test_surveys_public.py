"""Tests for public survey endpoints: tally authorization + submit rate limit."""

import json

import pytest
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

    def test_counts_choice_boolean_and_rating(self, api_client, survey_owner_headers, mixed_survey):
        response = api_client.get(self._url(mixed_survey), **survey_owner_headers)
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
        self, api_client, survey_owner, survey_owner_headers
    ):
        survey = Survey.objects.create(title="Empty", slug="empty", created_by=survey_owner)
        _question(survey, "Vibes", SurveyQuestionType.RATING)
        response = api_client.get(self._url(survey), **survey_owner_headers)
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
