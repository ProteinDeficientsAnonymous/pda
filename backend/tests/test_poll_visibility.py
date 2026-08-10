import json

import pytest
from community.models import Event, EventPoll, PageVisibility, PollOption
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def stranger_headers(db):
    stranger = User.objects.create_user(
        phone_number="+12025550707",
        password="strangerpass",
        first_name="Stranger",
    )
    refresh = RefreshToken.for_user(stranger)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def invitee_headers(db, invite_only_event):
    invitee = User.objects.create_user(
        phone_number="+12025550808",
        password="inviteepass",
        first_name="Invitee",
    )
    invite_only_event.invited_users.add(invitee)
    refresh = RefreshToken.for_user(invitee)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def invite_only_event(db, test_user):
    return Event.objects.create(
        title="Invite-only poll event",
        start_datetime=future_iso(days=30),
        created_by=test_user,
        visibility=PageVisibility.INVITE_ONLY,
    )


@pytest.fixture
def invite_only_poll(db, invite_only_event, test_user):
    poll = EventPoll.objects.create(event=invite_only_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    return poll


@pytest.mark.django_db
class TestGetPollVisibility:
    def test_anonymous_cannot_read_invite_only_poll(
        self, api_client, invite_only_event, invite_only_poll
    ):
        response = api_client.get(f"/api/community/events/{invite_only_event.id}/poll/")
        assert response.status_code == 403

    def test_non_invitee_cannot_read_invite_only_poll(
        self, api_client, stranger_headers, invite_only_event, invite_only_poll
    ):
        response = api_client.get(
            f"/api/community/events/{invite_only_event.id}/poll/",
            **stranger_headers,
        )
        assert response.status_code == 403

    def test_invitee_can_read_invite_only_poll(
        self, api_client, invitee_headers, invite_only_event, invite_only_poll
    ):
        response = api_client.get(
            f"/api/community/events/{invite_only_event.id}/poll/",
            **invitee_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["options"]) == 1

    def test_creator_can_read_invite_only_poll(
        self, api_client, auth_headers, invite_only_event, invite_only_poll
    ):
        response = api_client.get(
            f"/api/community/events/{invite_only_event.id}/poll/",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_anonymous_can_still_read_public_event_poll(self, api_client, db, test_user):
        event = Event.objects.create(
            title="Public poll event",
            start_datetime=future_iso(days=30),
            created_by=test_user,
        )
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
        response = api_client.get(f"/api/community/events/{event.id}/poll/")
        assert response.status_code == 200

    def test_anonymous_cannot_see_voter_identities_on_public_poll(self, api_client, db, test_user):
        from community.models import PollAvailability, PollVote

        event = Event.objects.create(
            title="Public poll event",
            start_datetime=future_iso(days=30),
            created_by=test_user,
        )
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        option = PollOption.objects.create(
            poll=poll, datetime=future_iso(days=120), display_order=0
        )

        voter1 = User.objects.create_user(
            phone_number="+12025550701",
            password="voter1pass",
            first_name="Voter1",
        )
        voter2 = User.objects.create_user(
            phone_number="+12025550702",
            password="voter2pass",
            first_name="Voter2",
        )
        PollVote.objects.create(option=option, user=voter1, availability=PollAvailability.YES)
        PollVote.objects.create(option=option, user=voter2, availability=PollAvailability.MAYBE)

        response = api_client.get(f"/api/community/events/{event.id}/poll/")
        assert response.status_code == 200
        data = response.json()
        assert len(data["options"]) == 1
        option_data = data["options"][0]
        assert option_data["yes_count"] == 1
        assert option_data["maybe_count"] == 1
        assert option_data["no_count"] == 0
        assert option_data["yes_voters"] == []
        assert option_data["maybe_voters"] == []
        assert option_data["no_voters"] == []

    def test_authenticated_can_see_voter_identities_on_public_poll(
        self, api_client, db, auth_headers, test_user
    ):
        from community.models import PollAvailability, PollVote

        event = Event.objects.create(
            title="Public poll event",
            start_datetime=future_iso(days=30),
            created_by=test_user,
        )
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        option = PollOption.objects.create(
            poll=poll, datetime=future_iso(days=120), display_order=0
        )

        voter1 = User.objects.create_user(
            phone_number="+12025550701",
            password="voter1pass",
            first_name="Voter1",
        )
        voter2 = User.objects.create_user(
            phone_number="+12025550702",
            password="voter2pass",
            first_name="Voter2",
        )
        PollVote.objects.create(option=option, user=voter1, availability=PollAvailability.YES)
        PollVote.objects.create(option=option, user=voter2, availability=PollAvailability.MAYBE)

        response = api_client.get(f"/api/community/events/{event.id}/poll/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["options"]) == 1
        option_data = data["options"][0]
        assert option_data["yes_count"] == 1
        assert option_data["maybe_count"] == 1
        assert option_data["no_count"] == 0
        assert len(option_data["yes_voters"]) == 1
        assert option_data["yes_voters"][0]["name"] == "Voter1"
        assert len(option_data["maybe_voters"]) == 1
        assert option_data["maybe_voters"][0]["name"] == "Voter2"
        assert option_data["no_voters"] == []


@pytest.mark.django_db
class TestVotePollVisibility:
    def _vote(self, api_client, event, poll, headers):
        option = poll.options.first()
        return api_client.post(
            f"/api/community/events/{event.id}/poll/vote/",
            data=json.dumps({"votes": {str(option.id): "yes"}}),
            content_type="application/json",
            **headers,
        )

    def test_non_invitee_cannot_vote_on_invite_only_poll(
        self, api_client, stranger_headers, invite_only_event, invite_only_poll
    ):
        response = self._vote(api_client, invite_only_event, invite_only_poll, stranger_headers)
        assert response.status_code == 403

    def test_invitee_can_vote_on_invite_only_poll(
        self, api_client, invitee_headers, invite_only_event, invite_only_poll
    ):
        response = self._vote(api_client, invite_only_event, invite_only_poll, invitee_headers)
        assert response.status_code == 200
