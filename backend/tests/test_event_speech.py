import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from community.models import (
    Event,
    EventSpeech,
    EventStatus,
    EventType,
    OfficialKind,
    PageVisibility,
    SpeechTemplate,
)
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._query_counts import assert_constant_queries
from tests._users import make_user

NY = ZoneInfo("America/New_York")


def _url(event: Event) -> str:
    return f"/api/community/events/{event.id}/speech/"


def _blank_pm(key: str) -> str:
    return json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "speechBlank", "attrs": {"key": key}}],
                }
            ],
        }
    )


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
    def test_unsaved_returns_prefill(self, api_client, maya, walk):
        template = SpeechTemplate.get()
        template.open_roles = ["greeter", "scribe"]
        template.shared_pm = _blank_pm("facilitators")
        template.save()
        _event(maya, title="walk on the hudson")
        _event(maya, title="community thing", event_type=EventType.COMMUNITY, official_kind="")
        _event(maya, title="cancelled", status=EventStatus.CANCELLED)
        _event(maya, title="earlier", start_datetime=datetime(2030, 5, 10, 18, 0, tzinfo=NY))

        response = api_client.get(_url(walk), **auth_headers_for(maya))

        assert response.status_code == 200
        data = response.json()
        assert data["saved"] is False
        assert data["official_kind"] == "walk"
        assert data["event_title"] == "walk on the hudson"
        assert data["html"] == ""
        assert data["updated_at"] is None
        assert data["updated_by_name"] is None
        assert data["values"]["facilitators"] == "maya and sam"
        assert data["values"]["open_roles"] == ["greeter", "scribe"]
        assert data["values"]["upcoming_events"] == ["5/23 walk on the hudson"]
        assert data["values"]["restaurant"] == ""

    def test_three_cohosts_use_three_cohosts_join_with_and(self, api_client, maya, sam, walk):
        zed = make_user(first_name="zed", is_member=True)
        walk.co_hosts.add(zed)
        data = api_client.get(_url(walk), **auth_headers_for(maya)).json()
        assert data["values"]["facilitators"] == "maya, sam and zed"

    def test_upcoming_excludes_the_event_itself(self, api_client, maya, walk):
        data = api_client.get(_url(walk), **auth_headers_for(maya)).json()
        assert data["values"]["upcoming_events"] == []

    @pytest.mark.parametrize(
        "visibility", [PageVisibility.MEMBERS_ONLY, PageVisibility.INVITE_ONLY]
    )
    def test_upcoming_skips_non_public_events(self, api_client, maya, walk, visibility):
        _event(maya, title="secret supper", visibility=visibility)
        data = api_client.get(_url(walk), **auth_headers_for(maya)).json()
        assert data["values"]["upcoming_events"] == []

    def test_restaurant_prefill_from_location(self, api_client, maya):
        event = _event(maya, kind=OfficialKind.RESTAURANT, location="Spicy Moon, 328 E 6th St")
        data = api_client.get(_url(event), **auth_headers_for(maya)).json()
        assert data["values"]["restaurant"] == "Spicy Moon"

    def test_restaurant_prefill_when_kind_unset(self, api_client, maya):
        event = _event(maya, kind="", location="Spicy Moon, 328 E 6th St")
        data = api_client.get(_url(event), **auth_headers_for(maya)).json()
        assert data["values"]["restaurant"] == "Spicy Moon"

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

    def test_walk_has_no_restaurant_prefill(self, api_client, maya):
        event = _event(maya, location="Spicy Moon, 328 E 6th St")
        data = api_client.get(_url(event), **auth_headers_for(maya)).json()
        assert data["values"]["restaurant"] == ""

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

    def test_switched_to_community_is_404_but_row_kept(self, api_client, maya, walk):
        api_client.put(
            _url(walk),
            {"values": {"facilitators": "x"}},
            content_type="application/json",
            **auth_headers_for(maya),
        )
        Event.objects.filter(pk=walk.pk).update(event_type=EventType.COMMUNITY)
        assert api_client.get(_url(walk), **auth_headers_for(maya)).status_code == 404
        assert EventSpeech.objects.filter(event_id=walk.pk).exists()

    def test_query_count_is_constant(self, api_client, maya, walk):
        def grow(n: int) -> None:
            for i in range(n):
                walk.co_hosts.add(
                    make_user(first_name=f"host{i}", last_name="Last", is_member=True)
                )
                _event(maya, title=f"later {i}")

        assert_constant_queries(api_client, _url(walk), grow, auth_headers_for(maya))


@pytest.mark.django_db
class TestPutSpeech:
    def _put(self, api_client, event, user, body):
        return api_client.put(
            _url(event), body, content_type="application/json", **auth_headers_for(user)
        )

    def test_put_then_get_is_saved_with_html(self, api_client, maya, walk):
        template = SpeechTemplate.get()
        template.shared_pm = _blank_pm("facilitators")
        template.save()

        put = self._put(api_client, walk, maya, {"values": {"facilitators": "maya and sam"}})
        assert put.status_code == 200
        assert "maya and sam" in put.json()["html"]

        data = api_client.get(_url(walk), **auth_headers_for(maya)).json()
        assert data["saved"] is True
        assert "maya and sam" in data["html"]
        assert data["values"]["facilitators"] == "maya and sam"
        assert data["updated_by_name"] == "maya"
        assert data["updated_at"] is not None

    def test_last_write_wins(self, api_client, maya, sam, walk):
        self._put(api_client, walk, maya, {"values": {"front_walker": "a"}})
        self._put(api_client, walk, sam, {"values": {"front_walker": "b"}})
        speech = EventSpeech.objects.get(event=walk)
        assert speech.values["front_walker"] == "b"
        assert speech.updated_by == sam

    def test_non_cohost_forbidden(self, api_client, walk):
        outsider = make_user(first_name="out", last_name="Last", is_member=True)
        assert self._put(api_client, walk, outsider, {"values": {}}).status_code == 403

    def test_manage_events_without_cohost_forbidden(self, api_client, walk):
        admin = make_user(PermissionKey.MANAGE_EVENTS, first_name="Admin", is_member=True)
        assert self._put(api_client, walk, admin, {"values": {}}).status_code == 403

    def test_anonymous_unauthorized(self, api_client, walk):
        response = api_client.put(_url(walk), {"values": {}}, content_type="application/json")
        assert response.status_code == 401

    def test_community_event_not_found(self, api_client, maya):
        event = _event(maya, event_type=EventType.COMMUNITY, official_kind="")
        assert self._put(api_client, event, maya, {"values": {}}).status_code == 404

    def test_bad_values_are_422(self, api_client, maya, walk):
        response = self._put(api_client, walk, maya, {"values": {"open_roles": "x"}})
        assert response.status_code == 422
        assert_error_code(response, "speech.invalid_values")
        assert not EventSpeech.objects.filter(event=walk).exists()
