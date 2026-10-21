"""Survey summary + CSV export on anonymous surveys and conditional questions."""

import csv
import io

import pytest
from community.models import (
    ShowIfOperator,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def surveys_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025557030", password="x", first_name="Surveys", last_name="Admin"
    )
    admin.roles.add(
        Role.objects.create(name="surveys_mgr", permissions=[PermissionKey.MANAGE_SURVEYS])
    )
    return admin


@pytest.fixture
def admin_headers(surveys_admin):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(surveys_admin).access_token}"}  # type: ignore


@pytest.fixture
def responder(db):
    return User.objects.create_user(
        phone_number="+12025557031", password="x", first_name="Secret", last_name="Responder"
    )


def _csv_rows(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def _csv_url(survey):
    return f"/api/community/surveys/{survey.id}/responses.csv"


def _summary_url(survey):
    return f"/api/community/surveys/{survey.id}/summary/"


@pytest.fixture
def anonymous_survey(db, surveys_admin, responder):
    survey = Survey.objects.create(
        title="Anon", slug="anon-report", created_by=surveys_admin, anonymous=True
    )
    q = SurveyQuestion.objects.create(
        survey=survey, label="Coming?", field_type=SurveyQuestionType.BOOLEAN, display_order=0
    )
    # even a row that somehow kept its user must not surface a name
    SurveyResponse.objects.create(
        survey=survey, user=responder, answers={str(q.id): {"label": q.label, "answer": "yes"}}
    )
    SurveyResponse.objects.create(
        survey=survey, user=None, answers={str(q.id): {"label": q.label, "answer": "no"}}
    )
    return survey


@pytest.mark.django_db
class TestAnonymousSurveyReports:
    def test_csv_drops_submitted_by_and_truncates_submitted_at(
        self, api_client, admin_headers, anonymous_survey
    ):
        response = api_client.get(_csv_url(anonymous_survey), **admin_headers)
        assert response.status_code == 200
        rows = _csv_rows(response)
        assert rows[0] == ["submitted_at", "Coming?"]
        days = {
            timezone.localtime(r.submitted_at)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat()
            for r in anonymous_survey.responses.all()
        }
        assert {row[0] for row in rows[1:]} == days
        assert "Secret" not in response.content.decode("utf-8-sig")

    def test_named_survey_csv_keeps_submitted_by(self, api_client, admin_headers, anonymous_survey):
        Survey.objects.filter(id=anonymous_survey.id).update(anonymous=False)
        rows = _csv_rows(api_client.get(_csv_url(anonymous_survey), **admin_headers))
        assert rows[0][0] == "submitted_by"
        assert "Secret Responder" in {row[0] for row in rows[1:]}

    def test_summary_has_counts_but_no_names(self, api_client, admin_headers, anonymous_survey):
        response = api_client.get(_summary_url(anonymous_survey), **admin_headers)
        assert response.status_code == 200
        [summary] = response.json()
        assert summary["counts"] == {"yes": 1, "no": 1}
        assert "Secret" not in response.content.decode()
        assert str(anonymous_survey.responses.exclude(user=None).get().user_id) not in (
            response.content.decode()
        )


@pytest.fixture
def conditional_survey(db, surveys_admin):
    survey = Survey.objects.create(title="Diet", slug="diet-report", created_by=surveys_admin)
    gate = SurveyQuestion.objects.create(
        survey=survey, label="Vegan?", field_type=SurveyQuestionType.BOOLEAN, display_order=0
    )
    follow_up = SurveyQuestion.objects.create(
        survey=survey,
        label="Favourite",
        field_type=SurveyQuestionType.RADIO,
        options=["tofu", "tempeh"],
        display_order=1,
        show_if={"question_id": str(gate.id), "operator": ShowIfOperator.EQUALS, "value": "yes"},
    )
    SurveyResponse.objects.create(
        survey=survey,
        answers={
            str(gate.id): {"label": gate.label, "answer": "yes"},
            str(follow_up.id): {"label": follow_up.label, "answer": "tofu"},
        },
    )
    SurveyResponse.objects.create(
        survey=survey, answers={str(gate.id): {"label": gate.label, "answer": "no"}}
    )
    return survey


@pytest.mark.django_db
class TestConditionalQuestionReports:
    def test_summary_skips_hidden_unanswered_questions(
        self, api_client, admin_headers, conditional_survey
    ):
        response = api_client.get(_summary_url(conditional_survey), **admin_headers)
        assert response.status_code == 200
        by_label = {
            q.label: s
            for q in conditional_survey.questions.all()
            for s in response.json()
            if s["question_id"] == str(q.id)
        }
        assert by_label["Vegan?"]["answered"] == 2
        assert by_label["Favourite"]["answered"] == 1
        assert by_label["Favourite"]["counts"] == {"tofu": 1, "tempeh": 0}

    def test_csv_leaves_hidden_question_blank(self, api_client, admin_headers, conditional_survey):
        response = api_client.get(_csv_url(conditional_survey), **admin_headers)
        assert response.status_code == 200
        rows = _csv_rows(response)
        assert rows[0] == ["submitted_by", "submitted_at", "Vegan?", "Favourite"]
        cells = {(row[2], row[3]) for row in rows[1:]}
        assert cells == {("yes", "tofu"), ("no", "")}
