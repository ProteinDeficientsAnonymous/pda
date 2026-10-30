import pytest
from community.models import Event, EventType, PageVisibility
from users.models import User
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._events import make_event
from tests._users import make_user

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def planner(db) -> User:
    return make_user(PermissionKey.TAG_OFFICIAL_EVENT, first_name="Plan")


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
    def test_existing_official_event_has_null_kind(self, api_client, planner):
        event = _event(planner)
        resp = api_client.get(f"{EVENTS_URL}{event.id}/", **auth_headers_for(planner))
        assert resp.status_code == 200
        assert resp.json()["official_kind"] is None
