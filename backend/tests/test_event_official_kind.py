import pytest
from community.models import Event, EventType, OfficialKind, PageVisibility
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
        "title": "Kind",
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
class TestOfficialKind:
    def test_create_official_event_saves_kind(self, api_client, planner):
        resp = _create(
            api_client, planner, event_type=EventType.OFFICIAL, official_kind=OfficialKind.WALK
        )
        assert resp.status_code == 201, resp.content
        assert resp.json()["official_kind"] == "walk"
        assert Event.objects.get(id=resp.json()["id"]).official_kind == OfficialKind.WALK

    def test_create_official_event_without_kind_is_null(self, api_client, planner):
        resp = _create(api_client, planner, event_type=EventType.OFFICIAL)
        assert resp.status_code == 201, resp.content
        assert resp.json()["official_kind"] is None

    def test_patch_official_kind(self, api_client, planner):
        event = _event(planner)
        resp = _patch(api_client, planner, event, official_kind=OfficialKind.RESTAURANT)
        assert resp.status_code == 200, resp.content
        assert resp.json()["official_kind"] == "restaurant"
        event.refresh_from_db()
        assert event.official_kind == OfficialKind.RESTAURANT

    def test_patch_null_kind_leaves_it_unchanged(self, api_client, planner):
        event = _event(planner, official_kind=OfficialKind.WALK)
        resp = _patch(api_client, planner, event, official_kind=None, title="Renamed")
        assert resp.status_code == 200, resp.content
        assert resp.json()["official_kind"] == "walk"
        event.refresh_from_db()
        assert event.official_kind == OfficialKind.WALK

    def test_patch_empty_kind_clears_it(self, api_client, planner):
        event = _event(planner, official_kind=OfficialKind.WALK)
        resp = _patch(api_client, planner, event, official_kind="")
        assert resp.status_code == 200, resp.content
        assert resp.json()["official_kind"] is None
        event.refresh_from_db()
        assert event.official_kind == ""

    def test_patch_switching_to_community_with_kind_rejected(self, api_client, planner):
        event = _event(planner, official_kind=OfficialKind.WALK)
        resp = _patch(
            api_client,
            planner,
            event,
            event_type=EventType.COMMUNITY,
            official_kind=OfficialKind.WALK,
        )
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_official_kind", "official_kind")

    def test_kind_rejected_on_community_event(self, api_client, member):
        resp = _create(
            api_client, member, event_type=EventType.COMMUNITY, official_kind=OfficialKind.WALK
        )
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_official_kind", "official_kind")

    def test_patch_kind_rejected_on_community_event(self, api_client, member):
        event = _event(member, EventType.COMMUNITY)
        resp = _patch(api_client, member, event, official_kind=OfficialKind.WALK)
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_official_kind", "official_kind")

    def test_invalid_kind_rejected_on_create(self, api_client, planner):
        resp = _create(api_client, planner, event_type=EventType.OFFICIAL, official_kind="picnic")
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_official_kind", "official_kind")

    def test_invalid_kind_rejected_on_patch(self, api_client, planner):
        event = _event(planner)
        resp = _patch(api_client, planner, event, official_kind="picnic")
        assert resp.status_code == 422
        assert_error_code(resp, "event.invalid_official_kind", "official_kind")

    def test_switching_to_community_clears_kind(self, api_client, planner):
        event = _event(planner, official_kind=OfficialKind.WALK)
        resp = _patch(api_client, planner, event, event_type=EventType.COMMUNITY)
        assert resp.status_code == 200, resp.content
        event.refresh_from_db()
        assert event.official_kind == ""

    def test_existing_official_event_has_null_kind(self, api_client, planner):
        event = _event(planner)
        resp = api_client.get(f"{EVENTS_URL}{event.id}/", **auth_headers_for(planner))
        assert resp.status_code == 200
        assert resp.json()["official_kind"] is None
