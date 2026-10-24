from datetime import timedelta

import pytest
from community._official_event_defaults import OFFICIAL_CASHAPP_LINK, OFFICIAL_RSVP_QUESTIONS
from community.models import Event, EventRsvpQuestion, EventType, PageVisibility
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests.conftest import future_iso

URL = "/api/community/official-event-defaults/"


@pytest.mark.django_db
class TestGetOfficialEventDefaults:
    def test_authenticated_user_gets_defaults(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "cashapp_link": OFFICIAL_CASHAPP_LINK,
            "rsvp_questions": [q.model_dump(mode="json") for q in OFFICIAL_RSVP_QUESTIONS],
        }

    def test_four_required_select_questions(self, api_client, auth_headers):
        questions = api_client.get(URL, **auth_headers).json()["rsvp_questions"]
        assert len(questions) == 4
        assert all(q["required"] and q["field_type"] == "select" for q in questions)

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401


EVENTS_URL = "/api/community/events/"
CUSTOM_QUESTION = {
    "label": "allergies?",
    "field_type": "textarea",
    "options": [],
    "required": False,
}


def _auth(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def planner(db) -> User:
    user = User.objects.create_user(phone_number="+12025556200", password="x", first_name="Plan")
    role = Role.objects.create(
        name="official_tagger", permissions=[PermissionKey.TAG_OFFICIAL_EVENT]
    )
    user.roles.add(role)
    return user


def _create(api_client, planner: User, **overrides) -> dict:
    payload = {
        "title": "Defaults",
        "start_datetime": future_iso(days=14),
        "visibility": PageVisibility.PUBLIC,
        **overrides,
    }
    response = api_client.post(
        EVENTS_URL, payload, content_type="application/json", **_auth(planner)
    )
    assert response.status_code == 201, response.content
    return response.json()


def _patch(api_client, planner: User, event_id: str, **changes) -> dict:
    response = api_client.patch(
        f"{EVENTS_URL}{event_id}/", changes, content_type="application/json", **_auth(planner)
    )
    assert response.status_code == 200, response.content
    return response.json()


def _labels(body: dict) -> list[str]:
    return [q["label"] for q in body["rsvp_questions"]]


OFFICIAL_LABELS = [q.label for q in OFFICIAL_RSVP_QUESTIONS]


@pytest.mark.django_db
class TestApplyOfficialDefaults:
    def test_create_official_fills_cashapp_and_questions(self, api_client, planner):
        body = _create(api_client, planner, event_type=EventType.OFFICIAL)
        assert body["cashapp_link"] == OFFICIAL_CASHAPP_LINK
        assert _labels(body) == OFFICIAL_LABELS
        stored = EventRsvpQuestion.objects.filter(event_id=body["id"]).order_by("display_order")
        assert [q.required for q in stored] == [True] * 4

    def test_create_official_keeps_what_was_sent(self, api_client, planner):
        body = _create(
            api_client,
            planner,
            event_type=EventType.OFFICIAL,
            cashapp_link="https://cash.app/$host",
            rsvp_questions=[CUSTOM_QUESTION],
        )
        assert body["cashapp_link"] == "https://cash.app/$host"
        assert _labels(body) == ["allergies?"]

    def test_create_community_gets_no_defaults(self, api_client, planner):
        body = _create(api_client, planner)
        assert body["cashapp_link"] == ""
        assert body["rsvp_questions"] == []

    def test_switching_to_official_fills_defaults(self, api_client, planner):
        event_id = _create(api_client, planner)["id"]
        body = _patch(api_client, planner, event_id, event_type=EventType.OFFICIAL)
        assert body["cashapp_link"] == OFFICIAL_CASHAPP_LINK
        assert _labels(body) == OFFICIAL_LABELS

    def test_switching_to_official_keeps_existing_cashapp_and_questions(self, api_client, planner):
        event_id = _create(
            api_client,
            planner,
            cashapp_link="https://cash.app/$host",
            rsvp_questions=[CUSTOM_QUESTION],
        )["id"]
        body = _patch(api_client, planner, event_id, event_type=EventType.OFFICIAL)
        assert body["cashapp_link"] == "https://cash.app/$host"
        assert _labels(body) == ["allergies?"]

    def test_editing_an_existing_official_event_adds_nothing(self, api_client, planner):
        event = Event.objects.create(
            title="Old official",
            event_type=EventType.OFFICIAL,
            visibility=PageVisibility.PUBLIC,
            start_datetime=timezone.now() + timedelta(days=7),
            created_by=planner,
        )
        body = _patch(api_client, planner, str(event.id), title="Renamed")
        assert body["cashapp_link"] == ""
        assert body["rsvp_questions"] == []
