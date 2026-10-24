from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventType,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _user(n: int, **extra) -> User:
    return User.objects.create_user(
        phone_number=f"+1202555{n:04d}", password="x", first_name=f"User{n}", **extra
    )


def _event(host: User, *, event_type=EventType.OFFICIAL) -> Event:
    return Event.objects.create(
        title="Potluck",
        event_type=event_type,
        start_datetime=timezone.now() - timedelta(days=2),
        end_datetime=timezone.now() - timedelta(days=2, hours=-2),
        created_by=host,
    )


@pytest.fixture
def host(db):
    return _user(1)


@pytest.fixture
def event(host):
    return _event(host)


@pytest.fixture
def survey(db):
    survey = Survey.objects.create(
        title="feedback", slug="official-feedback", feedback_event_type=EventType.OFFICIAL
    )
    SurveyQuestion.objects.create(
        survey=survey, label="how was it?", field_type=SurveyQuestionType.TEXT, display_order=0
    )
    return survey


def _response(survey: Survey, event: Event, answer: str = "great") -> SurveyResponse:
    question = survey.questions.first()
    return SurveyResponse.objects.create(
        survey=survey,
        event=event,
        answers={str(question.id): {"label": question.label, "answer": answer}},
    )


def _url(event: Event) -> str:
    return f"/api/community/events/{event.id}/feedback/"


@pytest.mark.django_db
class TestHostFeedback:
    def test_cohost_sees_responses_without_names_or_times(self, api_client, event, survey):
        cohost = _user(2)
        event.co_hosts.add(cohost)
        _response(survey, event)

        res = api_client.get(_url(event), **_auth(cohost))

        assert res.status_code == 200
        body = res.json()
        assert [q["label"] for q in body["questions"]] == ["how was it?"]
        [row] = body["responses"]
        assert set(row) == {"id", "answers", "submitted_on"}
        assert len(row["submitted_on"]) == 10
        assert "user_id" not in res.content.decode()
        assert "submitted_at" not in res.content.decode()

    def test_non_host_403(self, api_client, event, survey):
        assert api_client.get(_url(event), **_auth(_user(3))).status_code == 403

    def test_manage_events_admin_can_view(self, api_client, event, survey):
        admin = _user(4)
        admin.roles.add(Role.objects.create(name="ev", permissions=[PermissionKey.MANAGE_EVENTS]))
        _response(survey, event)

        res = api_client.get(_url(event), **_auth(admin))

        assert res.status_code == 200
        assert len(res.json()["responses"]) == 1

    def test_only_this_events_responses(self, api_client, host, event, survey):
        other_event = _event(host)
        _response(survey, event, "mine")
        _response(survey, other_event, "other")

        res = api_client.get(_url(event), **_auth(host))

        answers = [next(iter(r["answers"].values()))["answer"] for r in res.json()["responses"]]
        assert answers == ["mine"]

    def test_unknown_event_404(self, api_client, host):
        url = "/api/community/events/00000000-0000-0000-0000-000000000000/feedback/"

        assert api_client.get(url, **_auth(host)).status_code == 404

    def test_no_feedback_survey_returns_no_questions(self, api_client, host):
        res = api_client.get(_url(_event(host)), **_auth(host))

        assert res.json() == {"questions": [], "responses": []}

    def test_responses_newest_day_first(self, api_client, host, event, survey):
        old = _response(survey, event, "old")
        new = _response(survey, event, "new")
        SurveyResponse.objects.filter(pk=old.pk).update(
            submitted_at=timezone.now() - timedelta(days=3)
        )

        res = api_client.get(_url(event), **_auth(host))

        ids = [r["id"] for r in res.json()["responses"]]
        assert ids == [str(new.id), str(old.id)]
