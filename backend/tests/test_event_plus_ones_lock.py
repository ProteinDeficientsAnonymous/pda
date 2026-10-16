import pytest
from community.models import Event, EventType, PageVisibility
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def tagger(db):
    user = User.objects.create_user(
        phone_number="+14155557777",
        password="taggerpass123",
        first_name="Type",
        last_name="Tagger",
    )
    role = Role.objects.create(
        name="type_tagger",
        permissions=[PermissionKey.TAG_OFFICIAL_EVENT, PermissionKey.TAG_CLUB_EVENT],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def tagger_headers(tagger):
    refresh = RefreshToken.for_user(tagger)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _create(api_client, headers, event_type):
    return api_client.post(
        EVENTS_URL,
        {
            "title": "Locked +1s",
            "datetime_tbd": True,
            "event_type": event_type,
            "visibility": PageVisibility.PUBLIC,
            "allow_plus_ones": True,
        },
        content_type="application/json",
        **headers,
    )


def _patch(api_client, headers, event, **body):
    return api_client.patch(
        f"{EVENTS_URL}{event.id}/", body, content_type="application/json", **headers
    )


def _event(tagger, event_type, *, allow_plus_ones):
    return Event.objects.create(
        title="Existing",
        datetime_tbd=True,
        event_type=event_type,
        visibility=PageVisibility.PUBLIC,
        allow_plus_ones=allow_plus_ones,
        created_by=tagger,
    )


@pytest.mark.django_db
class TestCreate:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_official_and_club_force_plus_ones_off(self, api_client, tagger_headers, event_type):
        response = _create(api_client, tagger_headers, event_type)
        assert response.status_code == 201
        assert Event.objects.get(id=response.json()["id"]).allow_plus_ones is False

    def test_community_keeps_plus_ones(self, api_client, tagger_headers):
        response = _create(api_client, tagger_headers, EventType.COMMUNITY)
        assert response.status_code == 201
        assert Event.objects.get(id=response.json()["id"]).allow_plus_ones is True


@pytest.mark.django_db
class TestUpdate:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_cannot_turn_plus_ones_on(self, api_client, tagger, tagger_headers, event_type):
        event = _event(tagger, event_type, allow_plus_ones=False)
        response = _patch(api_client, tagger_headers, event, allow_plus_ones=True)
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.allow_plus_ones is False

    def test_switching_to_official_turns_plus_ones_off(self, api_client, tagger, tagger_headers):
        event = _event(tagger, EventType.COMMUNITY, allow_plus_ones=True)
        response = _patch(
            api_client,
            tagger_headers,
            event,
            event_type=EventType.OFFICIAL,
            allow_plus_ones=True,
        )
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.allow_plus_ones is False

    def test_existing_official_event_keeps_plus_ones(self, api_client, tagger, tagger_headers):
        event = _event(tagger, EventType.OFFICIAL, allow_plus_ones=True)
        response = _patch(
            api_client,
            tagger_headers,
            event,
            title="renamed",
            event_type=EventType.OFFICIAL,
            allow_plus_ones=True,
        )
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.allow_plus_ones is True

    def test_existing_official_event_can_turn_plus_ones_off(
        self, api_client, tagger, tagger_headers
    ):
        event = _event(tagger, EventType.OFFICIAL, allow_plus_ones=True)
        response = _patch(api_client, tagger_headers, event, allow_plus_ones=False)
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.allow_plus_ones is False

    def test_community_can_turn_plus_ones_on(self, api_client, tagger, tagger_headers):
        event = _event(tagger, EventType.COMMUNITY, allow_plus_ones=False)
        response = _patch(api_client, tagger_headers, event, allow_plus_ones=True)
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.allow_plus_ones is True
