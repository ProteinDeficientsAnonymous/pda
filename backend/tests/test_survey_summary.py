"""Tests for the per-question survey summary endpoint (Issue 1462)."""

from datetime import UTC, datetime, timedelta

import pytest
from community._validation import Code
from community.models import Event, Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


def _headers_for(user) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


def _user_with_role(phone: str, role_name: str, permission: str) -> User:
    user = User.objects.create_user(
        phone_number=phone, password="x", first_name="Role", last_name="Holder"
    )
    user.roles.add(Role.objects.create(name=role_name, permissions=[permission]))
    return user


@pytest.fixture
def survey_owner(db):
    return User.objects.create_user(
        phone_number="+12025557001", password="ownerpass", first_name="Survey", last_name="Owner"
    )


@pytest.fixture
def survey_owner_headers(survey_owner):
    return _headers_for(survey_owner)


@pytest.fixture
def surveys_admin_headers(db):
    return _headers_for(
        _user_with_role("+12025557020", "surveys_admin", PermissionKey.MANAGE_SURVEYS)
    )


@pytest.fixture
def events_admin_headers(db):
    return _headers_for(
        _user_with_role("+12025557021", "events_admin", PermissionKey.MANAGE_EVENTS)
    )


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
    rating = _question(survey, "Vibes", SurveyQuestionType.STARS, order=3)
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

    def test_event_id_filters_counts_to_that_event(
        self, api_client, surveys_admin_headers, mixed_survey
    ):
        start = datetime(2026, 3, 4, 18, tzinfo=UTC)
        event = Event.objects.create(
            title="potluck", start_datetime=start, end_datetime=start + timedelta(hours=2)
        )
        colour = mixed_survey.questions.get(label="Colour")
        blue = next(
            r for r in mixed_survey.responses.all() if r.answers[str(colour.id)]["answer"] == "blue"
        )
        blue.event = event
        blue.save(update_fields=["event"])

        response = api_client.get(
            f"{self._url(mixed_survey)}?event_id={event.id}", **surveys_admin_headers
        )
        assert response.status_code == 200
        rows = self._by_label(mixed_survey, response.json())
        assert rows["Colour"]["counts"] == {"red": 0, "blue": 1}
        assert rows["Colour"]["answered"] == 1

    @pytest.mark.parametrize("field_type", [SurveyQuestionType.STARS, SurveyQuestionType.SCALE])
    def test_rating_mean_is_none_without_answers(
        self, api_client, survey_owner, surveys_admin_headers, field_type
    ):
        survey = Survey.objects.create(title="Empty", slug="empty", created_by=survey_owner)
        _question(survey, "Vibes", field_type)
        response = api_client.get(self._url(survey), **surveys_admin_headers)
        assert response.status_code == 200
        assert response.json() == [
            {
                "question_id": str(survey.questions.get().id),
                "field_type": field_type,
                "counts": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "answered": 0,
                "mean": None,
            }
        ]

    def test_scale_counts_and_mean(self, api_client, survey_owner, surveys_admin_headers):
        survey = Survey.objects.create(title="Pace", slug="pace", created_by=survey_owner)
        pace = _question(survey, "Pace", SurveyQuestionType.SCALE)
        for answer in ("1", "4"):
            SurveyResponse.objects.create(
                survey=survey, user=None, answers=_answers({pace: answer})
            )
        [row] = api_client.get(self._url(survey), **surveys_admin_headers).json()
        assert row["counts"] == {"1": 1, "2": 0, "3": 0, "4": 1, "5": 0}
        assert row["mean"] == 2.5

    def test_answers_outside_current_options_keep_their_own_buckets(
        self, api_client, surveys_admin_headers, mixed_survey
    ):
        colour = mixed_survey.questions.get(label="Colour")
        colour.options = ["Red", "blue"]
        colour.save(update_fields=["options"])
        rating = mixed_survey.questions.get(label="Vibes")
        SurveyResponse.objects.create(
            survey=mixed_survey, user=None, answers=_answers({rating: "great"})
        )
        response = api_client.get(self._url(mixed_survey), **surveys_admin_headers)
        rows = self._by_label(mixed_survey, response.json())
        assert rows["Colour"]["counts"] == {"Red": 0, "blue": 1, "red": 2}
        assert rows["Colour"]["answered"] == 3
        assert rows["Vibes"]["counts"] == {"1": 0, "2": 1, "3": 0, "4": 0, "5": 1}
        assert rows["Vibes"]["answered"] == 2
        assert rows["Vibes"]["mean"] == 3.5

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
