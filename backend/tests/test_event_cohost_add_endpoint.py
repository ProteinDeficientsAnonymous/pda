import json

import pytest
from community.models import Event, EventCoHostInvite, EventStatus
from community.models.choices import CoHostInviteStatus
from users.models import User

from tests._auth import auth_headers_for
from tests._users import make_user
from tests.conftest import future_iso, past_iso


@pytest.fixture
def creator(db) -> User:
    return make_user(first_name="Creator")


@pytest.fixture
def alice(db) -> User:
    return make_user(first_name="Alice")


@pytest.fixture
def bob(db) -> User:
    return make_user(first_name="Bob")


@pytest.fixture
def outsider(db) -> User:
    return make_user(first_name="Outsider")


@pytest.fixture
def event(db, creator) -> Event:
    event = Event.objects.create(
        title="Potluck",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        status=EventStatus.ACTIVE,
        created_by=creator,
    )
    event.co_hosts.add(creator)
    return event


def _add_cohosts(api_client, event, user, ids):
    return api_client.post(
        f"/api/community/events/{event.id}/cohost-invites/",
        data=json.dumps({"user_ids": [str(i) for i in ids]}),
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.django_db
class TestAddCohostsEndpoint:
    def test_adding_a_cohost_leaves_existing_pending_invites_alone(
        self, api_client, event, creator, alice, bob
    ):
        """The regression this endpoint exists to prevent."""
        _add_cohosts(api_client, event, creator, [alice.id])
        _add_cohosts(api_client, event, creator, [bob.id])

        assert (
            EventCoHostInvite.objects.get(event=event, user=alice).status
            == CoHostInviteStatus.PENDING
        )
        assert (
            EventCoHostInvite.objects.get(event=event, user=bob).status
            == CoHostInviteStatus.PENDING
        )

    def test_response_includes_the_new_pending_invite(self, api_client, event, creator, alice):
        resp = _add_cohosts(api_client, event, creator, [alice.id])

        assert resp.status_code == 200
        pending = resp.json()["pending_cohost_invites"]
        assert [p["user_id"] for p in pending] == [str(alice.id)]

    def test_re_adding_an_already_pending_user_is_a_noop(self, api_client, event, creator, alice):
        _add_cohosts(api_client, event, creator, [alice.id])
        resp = _add_cohosts(api_client, event, creator, [alice.id])

        assert resp.status_code == 200
        assert EventCoHostInvite.objects.filter(event=event, user=alice).count() == 1

    def test_non_host_cannot_add_cohosts(self, api_client, event, outsider, alice):
        resp = _add_cohosts(api_client, event, outsider, [alice.id])

        assert resp.status_code == 403
        assert not EventCoHostInvite.objects.filter(event=event, user=alice).exists()

    def test_cannot_invite_to_a_past_event(self, api_client, db, creator, alice):
        past = Event.objects.create(
            title="Last Month",
            start_datetime=past_iso(days=30),
            end_datetime=past_iso(days=29),
            status=EventStatus.ACTIVE,
            created_by=creator,
        )
        past.co_hosts.add(creator)

        resp = _add_cohosts(api_client, past, creator, [alice.id])

        assert resp.status_code == 400
        assert not EventCoHostInvite.objects.filter(event=past, user=alice).exists()

    def test_empty_user_ids_is_rejected(self, api_client, event, creator):
        resp = _add_cohosts(api_client, event, creator, [])

        assert resp.status_code == 422
