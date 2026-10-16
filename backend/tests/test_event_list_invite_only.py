import pytest
from community.models import Event, EventStatus, PageVisibility
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests.conftest import future_iso


def _user(phone: str, name: str) -> User:
    return User.objects.create_user(phone_number=phone, password="Testpass123!", first_name=name)


def _headers(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


def _listed(api_client, user: User, status: str = EventStatus.ACTIVE) -> list[dict]:
    response = api_client.get(f"/api/community/events/?status={status}", **_headers(user))
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def party(db):
    creator = _user("+12025551001", "Creator")
    cohosts = [_user(f"+1202555110{i}", f"Co{i}") for i in range(3)]
    invitees = [_user(f"+1202555120{i}", f"Inv{i}") for i in range(3)]
    event = Event.objects.create(
        title="Private party",
        start_datetime=future_iso(days=5),
        created_by=creator,
        visibility=PageVisibility.INVITE_ONLY,
    )
    event.co_hosts.add(*cohosts)
    event.invited_users.add(*invitees, cohosts[0])
    return event, creator, cohosts, invitees


def _manage_events_user() -> User:
    user = _user("+12025551301", "Manager")
    user.roles.add(Role.objects.create(name="ev_mgr", permissions=[PermissionKey.MANAGE_EVENTS]))
    return user


def _admin_user() -> User:
    user = _user("+12025551302", "Admin")
    user.roles.add(Role.objects.get(name="admin", is_default=True))
    return user


@pytest.mark.django_db
class TestInviteOnlyListVisibility:
    @pytest.mark.parametrize(
        "pick",
        [
            lambda creator, cohosts, invitees: creator,
            lambda creator, cohosts, invitees: cohosts[1],
            lambda creator, cohosts, invitees: invitees[1],
            lambda creator, cohosts, invitees: cohosts[0],  # co-host and invited
            lambda *_: _manage_events_user(),
            lambda *_: _admin_user(),
        ],
        ids=["creator", "cohost", "invitee", "cohost-and-invitee", "manage-events", "admin"],
    )
    def test_allowed_viewers_see_it_once(self, api_client, party, pick):
        event, creator, cohosts, invitees = party
        viewer = pick(creator, cohosts, invitees)
        ids = [e["id"] for e in _listed(api_client, viewer)]
        assert ids.count(str(event.id)) == 1

    def test_uninvited_member_does_not_see_it(self, api_client, party):
        event, *_ = party
        stranger = _user("+12025551303", "Stranger")
        assert str(event.id) not in [e["id"] for e in _listed(api_client, stranger)]

    def test_public_event_listed_once_with_many_cohosts(self, api_client, party):
        _event, creator, cohosts, invitees = party
        public = Event.objects.create(
            title="Open", start_datetime=future_iso(days=6), created_by=creator
        )
        public.co_hosts.add(*cohosts)
        public.invited_users.add(*invitees)
        ids = [e["id"] for e in _listed(api_client, cohosts[0])]
        assert ids.count(str(public.id)) == 1


@pytest.mark.django_db
class TestOwnDraftsList:
    def test_creator_and_cohost_see_draft_once_others_do_not(self, api_client):
        creator = _user("+12025551401", "Creator")
        cohost = _user("+12025551402", "Cohost")
        stranger = _user("+12025551403", "Stranger")
        draft = Event.objects.create(
            title="Draft", created_by=creator, status=EventStatus.DRAFT, datetime_tbd=True
        )
        draft.co_hosts.add(cohost)
        for viewer, expected in ((creator, 1), (cohost, 1), (stranger, 0)):
            ids = [e["id"] for e in _listed(api_client, viewer, EventStatus.DRAFT)]
            assert ids.count(str(draft.id)) == expected
