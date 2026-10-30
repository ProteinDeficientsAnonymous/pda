from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from community.models import (
    Event,
    EventStatus,
    EventType,
    OfficialKind,
)
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._events import make_event
from tests._query_counts import assert_constant_queries
from tests._users import make_user

NY = ZoneInfo("America/New_York")


def _url(event: Event) -> str:
    return f"/api/community/events/{event.id}/speech/"


def _event(creator, *, kind: str = OfficialKind.WALK, days: int = 1, **kwargs) -> Event:
    defaults = {
        "title": "walk on the hudson",
        "event_type": EventType.OFFICIAL,
        "official_kind": kind,
        "start_datetime": datetime(2030, 5, 23, 18, 0, tzinfo=NY),
        "created_by": creator,
    }
    return make_event(**{**defaults, **kwargs})


@pytest.fixture
def maya(db):
    return make_user(first_name="maya", is_member=True)


@pytest.fixture
def sam(db):
    return make_user(first_name="sam", is_member=True)


@pytest.fixture
def walk(maya, sam):
    event = _event(maya, start_datetime=datetime(2030, 5, 20, 18, 0, tzinfo=NY))
    event.co_hosts.add(sam)
    return event


@pytest.mark.django_db
class TestGetSpeech:
    def test_facilitators_prefill_is_viewer_independent(self, api_client, maya, walk):
        hidden = make_user(first_name="zed", last_name="Secret", is_member=True)
        hidden.hide_last_name = True
        hidden.save(update_fields=["hide_last_name"])
        walk.co_hosts.add(hidden)
        admin = make_user(PermissionKey.MANAGE_EVENTS, first_name="Ad", last_name="Min")
        walk.co_hosts.add(admin)
        for viewer in (admin, hidden):
            data = api_client.get(_url(walk), **auth_headers_for(viewer)).json()
            assert "Secret" not in data["values"]["facilitators"]
            assert "zed" in data["values"]["facilitators"]

    def test_non_cohost_member_forbidden(self, api_client, walk):
        outsider = make_user(first_name="out", last_name="Last", is_member=True)
        assert api_client.get(_url(walk), **auth_headers_for(outsider)).status_code == 403

    def test_manage_events_without_cohost_forbidden(self, api_client, walk):
        admin = make_user(PermissionKey.MANAGE_EVENTS, first_name="Admin", is_member=True)
        assert api_client.get(_url(walk), **auth_headers_for(admin)).status_code == 403

    def test_anonymous_unauthorized(self, api_client, walk):
        assert api_client.get(_url(walk)).status_code == 401

    def test_community_event_not_found(self, api_client, maya):
        event = _event(maya, event_type=EventType.COMMUNITY, official_kind="")
        assert api_client.get(_url(event), **auth_headers_for(maya)).status_code == 404

    def test_deleted_event_not_found(self, api_client, maya, walk):
        Event.objects.filter(pk=walk.pk).update(status=EventStatus.DELETED)
        assert api_client.get(_url(walk), **auth_headers_for(maya)).status_code == 404

    def test_not_found_checked_before_permission(self, api_client):
        outsider = make_user(first_name="out", last_name="Last", is_member=True)
        community = _event(outsider, event_type=EventType.COMMUNITY, official_kind="")
        other = make_user(first_name="other", last_name="Last", is_member=True)
        assert api_client.get(_url(community), **auth_headers_for(other)).status_code == 404

    def test_event_without_kind_reports_none(self, api_client, maya):
        event = _event(maya, kind="")
        data = api_client.get(_url(event), **auth_headers_for(maya)).json()
        assert data["official_kind"] is None

    def test_query_count_is_constant(self, api_client, maya, walk):
        def grow(n: int) -> None:
            for i in range(n):
                walk.co_hosts.add(
                    make_user(first_name=f"host{i}", last_name="Last", is_member=True)
                )
                _event(maya, title=f"later {i}")

        assert_constant_queries(api_client, _url(walk), grow, auth_headers_for(maya))
