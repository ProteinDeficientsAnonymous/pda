"""Tests for EventPoll endpoints: create, get, vote, finalize, delete."""

import json

import pytest
from community.models import Event, EventPoll, PollAvailability, PollOption, PollVote
from users.models import User  # noqa: F401 (imported for create_user side effect)

from tests.conftest import future_iso

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def poll_event(db, test_user):
    return Event.objects.create(
        title="Poll Event",
        start_datetime=future_iso(days=90),
        created_by=test_user,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550202",
        password="otherpass",
        display_name="Other Member",
    )


@pytest.fixture
def other_headers(other_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def poll_with_options(db, poll_event, test_user):
    poll = EventPoll.objects.create(event=poll_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=121), display_order=1)
    return poll


# ---------------------------------------------------------------------------
# TestCreatePoll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreatePoll:
    def test_create_poll_success(self, api_client, auth_headers, poll_event):
        payload = {"options": [future_iso(days=120), future_iso(days=121), future_iso(days=122)]}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_id"] == str(poll_event.id)
        assert data["is_active"] is True
        assert len(data["options"]) == 3
        assert data["winning_option_id"] is None
        # datetime_tbd should be set on the event
        poll_event.refresh_from_db()
        assert poll_event.datetime_tbd is True

    def test_create_poll_requires_at_least_one_option(self, api_client, auth_headers, poll_event):
        payload = {"options": []}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_create_poll_with_one_option_succeeds(self, api_client, auth_headers, poll_event):
        payload = {"options": [future_iso(days=120)]}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201

    def test_create_poll_duplicate_fails(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        payload = {"options": [future_iso(days=150), future_iso(days=151)]}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_create_poll_non_creator_forbidden(self, api_client, other_headers, poll_event):
        payload = {"options": [future_iso(days=120), future_iso(days=121)]}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403

    def test_create_poll_unauthenticated(self, api_client, poll_event):
        payload = {"options": [future_iso(days=120), future_iso(days=121)]}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_create_poll_event_not_found(self, api_client, auth_headers):
        import uuid

        payload = {"options": [future_iso(days=120), future_iso(days=121)]}
        response = api_client.post(
            f"/api/community/events/{uuid.uuid4()}/poll/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestGetPoll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetPoll:
    def test_get_poll_anonymous(self, api_client, poll_with_options, poll_event):
        response = api_client.get(f"/api/community/events/{poll_event.id}/poll/")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == str(poll_event.id)
        assert len(data["options"]) == 2
        assert data["my_votes"] == {}

    def test_get_poll_includes_my_votes(
        self, api_client, auth_headers, poll_with_options, poll_event, test_user
    ):
        option = poll_with_options.options.first()
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)
        response = api_client.get(f"/api/community/events/{poll_event.id}/poll/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["my_votes"][str(option.id)] == PollAvailability.YES

    def test_get_poll_not_found(self, api_client, poll_event):
        response = api_client.get(f"/api/community/events/{poll_event.id}/poll/")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestVoteOnPoll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVoteOnPoll:
    def test_vote_success(self, api_client, auth_headers, poll_with_options, poll_event):
        options = list(poll_with_options.options.all())
        payload = {
            "votes": {
                str(options[0].id): PollAvailability.YES,
                str(options[1].id): PollAvailability.MAYBE,
            }
        }
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["my_votes"][str(options[0].id)] == PollAvailability.YES
        assert data["my_votes"][str(options[1].id)] == PollAvailability.MAYBE

    def test_vote_updates_existing(
        self, api_client, auth_headers, poll_with_options, poll_event, test_user
    ):
        option = poll_with_options.options.first()
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)
        payload = {"votes": {str(option.id): PollAvailability.MAYBE}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_votes"][str(option.id)] == PollAvailability.MAYBE
        assert PollVote.objects.filter(option=option, user=test_user).count() == 1

    def test_vote_retracts_removed_options(
        self, api_client, auth_headers, poll_with_options, poll_event, test_user
    ):
        options = list(poll_with_options.options.all())
        PollVote.objects.create(
            option=options[0], user=test_user, availability=PollAvailability.YES
        )
        PollVote.objects.create(
            option=options[1], user=test_user, availability=PollAvailability.MAYBE
        )
        # Submit only one option — the other should be retracted
        payload = {"votes": {str(options[0].id): PollAvailability.YES}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert str(options[1].id) not in response.json()["my_votes"]

    def test_vote_invalid_availability(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        payload = {"votes": {str(option.id): "definitely"}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_vote_invalid_option_id(self, api_client, auth_headers, poll_with_options, poll_event):
        import uuid

        payload = {"votes": {str(uuid.uuid4()): PollAvailability.YES}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_vote_unauthenticated(self, api_client, poll_with_options, poll_event):
        option = poll_with_options.options.first()
        payload = {"votes": {str(option.id): PollAvailability.YES}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_vote_no_availability(self, api_client, auth_headers, poll_with_options, poll_event):
        option = poll_with_options.options.first()
        payload = {"votes": {str(option.id): PollAvailability.NO}}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/vote/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["my_votes"][str(option.id)] == PollAvailability.NO
        # Verify no_count is returned in the option
        opt_data = next(o for o in data["options"] if o["id"] == str(option.id))
        assert opt_data["no_count"] == 1


# ---------------------------------------------------------------------------
# TestFinalizePoll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFinalizePoll:
    def test_finalize_success(self, api_client, auth_headers, poll_with_options, poll_event):
        option = poll_with_options.options.first()
        payload = {"winning_option_id": str(option.id)}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["winning_option_id"] == str(option.id)
        assert data["is_active"] is False
        # Event datetime should be updated
        poll_event.refresh_from_db()
        assert poll_event.datetime_tbd is False

    def test_finalize_updates_event_datetime(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        payload = {"winning_option_id": str(option.id)}
        api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        poll_event.refresh_from_db()
        option.refresh_from_db()
        assert poll_event.start_datetime == option.datetime

    def test_finalize_already_finalized(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        poll_with_options.winning_option = option
        poll_with_options.save(update_fields=["winning_option"])
        payload = {"winning_option_id": str(option.id)}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_finalize_invalid_option(self, api_client, auth_headers, poll_with_options, poll_event):
        import uuid

        payload = {"winning_option_id": str(uuid.uuid4())}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_finalize_non_creator_forbidden(
        self, api_client, other_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        payload = {"winning_option_id": str(option.id)}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403

    def test_co_host_can_finalize(
        self, api_client, poll_with_options, poll_event, other_user, other_headers
    ):
        poll_event.co_hosts.add(other_user)
        option = poll_with_options.options.first()
        payload = {"winning_option_id": str(option.id)}
        response = api_client.post(
            f"/api/community/events/{poll_event.id}/poll/finalize/",
            data=json.dumps(payload),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TestDeletePoll
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeletePoll:
    def test_delete_success(self, api_client, auth_headers, poll_with_options, poll_event):
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/",
            **auth_headers,
        )
        assert response.status_code == 204
        assert not EventPoll.objects.filter(event=poll_event).exists()

    def test_delete_cascades_options_and_votes(
        self, api_client, auth_headers, poll_with_options, poll_event, test_user
    ):
        option = poll_with_options.options.first()
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)
        api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/",
            **auth_headers,
        )
        assert not PollOption.objects.filter(poll=poll_with_options).exists()
        assert not PollVote.objects.filter(option=option).exists()

    def test_delete_non_creator_forbidden(
        self, api_client, other_headers, poll_with_options, poll_event
    ):
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/",
            **other_headers,
        )
        assert response.status_code == 403

    def test_delete_not_found(self, api_client, auth_headers, poll_event):
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/",
            **auth_headers,
        )
        assert response.status_code == 404
