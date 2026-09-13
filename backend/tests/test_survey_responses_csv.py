"""Tests for the survey responses CSV export (Issue 1462)."""

import csv
import io

import pytest
from community._validation import Code
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code

POLL_A = "2030-01-01T10:00:00+00:00"
POLL_B = "2030-01-02T10:00:00+00:00"


@pytest.fixture
def surveys_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025557020",
        password="x",
        first_name="Surveys",
        last_name="Admin",
    )
    role = Role.objects.create(name="surveys_mgr", permissions=[PermissionKey.MANAGE_SURVEYS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def admin_headers(surveys_admin):
    refresh = RefreshToken.for_user(surveys_admin)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def csv_survey(db, surveys_admin):
    survey = Survey.objects.create(title="Export me", slug="export-me", created_by=surveys_admin)
    text = SurveyQuestion.objects.create(
        survey=survey, label="Notes", field_type=SurveyQuestionType.TEXT, display_order=0
    )
    checkbox = SurveyQuestion.objects.create(
        survey=survey,
        label="Toppings",
        field_type=SurveyQuestionType.CHECKBOX,
        options=["tofu", "kale"],
        display_order=1,
    )
    poll = SurveyQuestion.objects.create(
        survey=survey,
        label="When",
        field_type=SurveyQuestionType.DATETIME_POLL,
        options=[POLL_A, POLL_B],
        display_order=2,
    )
    SurveyResponse.objects.create(
        survey=survey,
        user=surveys_admin,
        answers={
            str(text.id): {"label": "Notes", "answer": "=SUM(A1)"},
            str(checkbox.id): {"label": "Toppings", "answer": "tofu,kale"},
            str(poll.id): {"label": "When", "answer": {POLL_B: "maybe", POLL_A: "yes"}},
        },
    )
    SurveyResponse.objects.create(
        survey=survey,
        user=None,
        answers={str(text.id): {"label": "Notes", "answer": "hello, world"}},
    )
    return survey


def _url(survey):
    return f"/api/community/surveys/{survey.id}/responses.csv"


def _rows(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.content.decode())))


@pytest.mark.django_db
class TestSurveyResponsesCsv:
    def test_one_row_per_response_with_question_columns(
        self, api_client, admin_headers, csv_survey
    ):
        response = api_client.get(_url(csv_survey), **admin_headers)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"] == (
            f'attachment; filename="survey-responses-{csv_survey.id}.csv"'
        )
        rows = _rows(response)
        assert rows[0] == ["submitted_by", "submitted_at", "Notes", "Toppings", "When"]
        assert len(rows) == 3
        by_name = {row[0]: row for row in rows[1:]}
        admin_row = by_name["Surveys Admin"]
        assert admin_row[2] == "'=SUM(A1)"
        assert admin_row[3] == "tofu,kale"
        assert admin_row[4] == f"{POLL_A}=yes;{POLL_B}=maybe"
        anon_row = by_name[""]
        assert anon_row[2] == "hello, world"
        assert anon_row[3] == ""
        assert anon_row[4] == ""

    def test_submitted_at_is_iso(self, api_client, admin_headers, csv_survey):
        rows = _rows(api_client.get(_url(csv_survey), **admin_headers))
        submitted = {r.submitted_at.isoformat() for r in csv_survey.responses.all()}
        assert {row[1] for row in rows[1:]} == submitted

    def test_requires_manage_surveys(self, api_client, auth_headers, csv_survey):
        response = api_client.get(_url(csv_survey), **auth_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_unauthenticated_401(self, api_client, csv_survey):
        assert api_client.get(_url(csv_survey)).status_code == 401

    def test_missing_survey_404(self, api_client, admin_headers):
        response = api_client.get(
            "/api/community/surveys/00000000-0000-0000-0000-000000000000/responses.csv",
            **admin_headers,
        )
        assert response.status_code == 404
