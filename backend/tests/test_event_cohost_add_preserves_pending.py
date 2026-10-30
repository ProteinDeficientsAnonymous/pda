import json

import pytest
from community.models import Event, EventCoHostInvite, EventStatus
from community.models.choices import CoHostInviteStatus
from users.models import User

from tests._auth import auth_headers_for
from tests._users import make_user
from tests.conftest import future_iso


@pytest.fixture
def creator(db) -> User:
    return make_user(first_name="Creator")


@pytest.fixture
def first_invitee(db) -> User:
    return make_user(first_name="First")


@pytest.fixture
def second_invitee(db) -> User:
    return make_user(first_name="Second")


@pytest.fixture
def event(db, creator) -> Event:
    return Event.objects.create(
        title="Potluck",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        status=EventStatus.ACTIVE,
        created_by=creator,
    )


def _patch_cohosts(api_client, event, user, ids):
    return api_client.patch(
        f"/api/community/events/{event.id}/",
        data=json.dumps({"co_host_ids": [str(i) for i in ids]}),
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.django_db
class TestAddCohostPreservesPendingInvites:
    def test_adding_a_cohost_does_not_rescind_an_existing_pending_invite(
        self, api_client, event, creator, first_invitee, second_invitee
    ):
        _patch_cohosts(api_client, event, creator, [first_invitee.id])
        assert (
            EventCoHostInvite.objects.get(event=event, user=first_invitee).status
            == CoHostInviteStatus.PENDING
        )

        # Adding a second co-host must not drop the first, still-pending invite.
        _patch_cohosts(api_client, event, creator, [first_invitee.id, second_invitee.id])

        first = EventCoHostInvite.objects.get(event=event, user=first_invitee)
        second = EventCoHostInvite.objects.get(event=event, user=second_invitee)
        assert first.status == CoHostInviteStatus.PENDING
        assert second.status == CoHostInviteStatus.PENDING

    def test_patch_response_includes_the_newly_invited_cohost(
        self, api_client, event, creator, first_invitee
    ):
        resp = _patch_cohosts(api_client, event, creator, [first_invitee.id])

        assert resp.status_code == 200
        pending = resp.json()["pending_cohost_invites"]
        assert [p["user_id"] for p in pending] == [str(first_invitee.id)]

    def test_payload_omitting_pending_invitee_rescinds_them(
        self, api_client, event, creator, first_invitee, second_invitee
    ):
        """Guards the contract AddCoHostDialog relies on: an id absent from
        co_host_ids is a removal, so callers must resend pending invitees."""
        _patch_cohosts(api_client, event, creator, [first_invitee.id])

        _patch_cohosts(api_client, event, creator, [second_invitee.id])

        first = EventCoHostInvite.objects.get(event=event, user=first_invitee)
        assert first.status == CoHostInviteStatus.RESCINDED
