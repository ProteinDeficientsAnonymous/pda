import pytest
from community.models import Event, EventFormat, EventType, PageVisibility
from users.models import User
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._time import future_iso
from tests._users import make_user

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def planner(db) -> User:
    return make_user(PermissionKey.TAG_OFFICIAL_EVENT, first_name="Plan")


@pytest.fixture
def member(db) -> User:
    return make_user(first_name="Mem")


def _create(api_client, user: User, **overrides):
    payload = {
        "title": "Format",
        "start_datetime": future_iso(days=14),
        "visibility": PageVisibility.PUBLIC,
        **overrides,
    }
    return api_client.post(
        EVENTS_URL, payload, content_type="application/json", **auth_headers_for(user)
    )


def _patch(api_client, user: User, event: Event, **changes):
    return api_client.patch(
        f"{EVENTS_URL}{event.id}/",
        changes,
        content_type="application/json",
        **auth_headers_for(user),
    )


def _event(creator: User, event_type: str = EventType.OFFICIAL, **kwargs) -> Event:
    return make_event(
        title="Existing",
        event_type=event_type,
        visibility=PageVisibility.PUBLIC,
        created_by=creator,
        **kwargs,
    )


@pytest.mark.django_db
class TestEventFormat:
    def test_create_official_event_saves_format(self, api_client, planner):
        resp = _create(
            api_client, planner, event_type=EventType.OFFICIAL, event_format=EventFormat.WALK
        )
        assert resp.status_code == 201, resp.content
        assert resp.json()["event_format"] == "walk"
        assert Event.objects.get(id=resp.json()["id"]).event_format == EventFormat.WALK

    def test_create_official_event_without_format_is_null(self, api_client, planner):
        resp = _create(api_client, planner, event_type=EventType.OFFICIAL)
        assert resp.status_code == 201, resp.content
        assert resp.json()["event_format"] is None

    def test_patch_event_format(self, api_client, planner):
        event = _event(planner)
        resp = _patch(api_client, planner, event, event_format=EventFormat.RESTAURANT)
        assert resp.status_code == 200, resp.content
        assert resp.json()["event_format"] == "restaurant"
        event.refresh_from_db()
        assert event.event_format == EventFormat.RESTAURANT

    def test_patch_null_format_leaves_it_unchanged(self, api_client, planner):
        event = _event(planner, event_format=EventFormat.WALK)
        resp = _patch(api_client, planner, event, event_format=None, title="Renamed")
        assert resp.status_code == 200, resp.content
        assert resp.json()["event_format"] == "walk"
        event.refresh_from_db()
        assert event.event_format == EventFormat.WALK

    def test_patch_empty_format_clears_it(self, api_client, planner):
        event = _event(planner, event_format=EventFormat.WALK)
        resp = _patch(api_client, planner, event, event_format="")
        assert resp.status_code == 200, resp.content
        assert resp.json()["event_format"] is None
        event.refresh_from_db()
        assert event.event_format == ""

    def test_patch_switching_to_community_with_format_rejected(self, api_client, planner):
        event = _event(planner, event_format=EventFormat.WALK)
        resp = _patch(
            api_client,
            planner,
            event,
            event_type=EventType.COMMUNITY,
            event_format=EventFormat.WALK,
        )
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_event_format", "event_format")

    def test_format_rejected_on_community_event(self, api_client, member):
        resp = _create(
            api_client, member, event_type=EventType.COMMUNITY, event_format=EventFormat.WALK
        )
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_event_format", "event_format")

    def test_patch_format_rejected_on_community_event(self, api_client, member):
        event = _event(member, EventType.COMMUNITY)
        resp = _patch(api_client, member, event, event_format=EventFormat.WALK)
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_event_format", "event_format")

    def test_invalid_format_rejected_on_create(self, api_client, planner):
        resp = _create(api_client, planner, event_type=EventType.OFFICIAL, event_format="picnic")
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_event_format", "event_format")

    def test_invalid_format_rejected_on_patch(self, api_client, planner):
        event = _event(planner)
        resp = _patch(api_client, planner, event, event_format="picnic")
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_event_format", "event_format")

    def test_switching_to_community_clears_format(self, api_client, planner):
        event = _event(planner, event_format=EventFormat.WALK)
        resp = _patch(api_client, planner, event, event_type=EventType.COMMUNITY)
        assert resp.status_code == 200, resp.content
        event.refresh_from_db()
        assert event.event_format == ""

    def test_existing_official_event_has_null_format(self, api_client, planner):
        event = _event(planner)
        resp = api_client.get(f"{EVENTS_URL}{event.id}/", **auth_headers_for(planner))
        assert resp.status_code == 200
        assert resp.json()["event_format"] is None
