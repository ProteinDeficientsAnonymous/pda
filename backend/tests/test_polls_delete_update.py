"""Tests for EventPoll delete/update endpoints: delete poll, delete option, update option."""

import json
import uuid

import pytest
from community.models import Event, EventPoll, PollAvailability, PollOption, PollVote
from ninja_jwt.tokens import RefreshToken
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
        first_name="Other",
        last_name="Member",
    )


@pytest.fixture
def other_headers(other_user):
    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def poll_with_options(db, poll_event, test_user):
    poll = EventPoll.objects.create(event=poll_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=121), display_order=1)
    return poll


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


# ---------------------------------------------------------------------------
# TestDeletePollOption
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeletePollOption:
    def test_delete_option_cannot_delete_when_only_two_options(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/options/{option.id}/",
            **auth_headers,
        )
        assert response.status_code == 400
        poll_with_options.refresh_from_db()
        assert poll_with_options.options.count() == 2

    def test_delete_option_non_creator_forbidden(
        self, api_client, other_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/options/{option.id}/",
            **other_headers,
        )
        assert response.status_code == 403

    def test_delete_option_not_found(self, api_client, auth_headers, poll_event, poll_with_options):
        response = api_client.delete(
            f"/api/community/events/{poll_event.id}/poll/options/{uuid.uuid4()}/",
            **auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestUpdatePollOption:
    def test_update_clears_votes_on_changed_option(
        self, api_client, auth_headers, poll_with_options, poll_event, test_user
    ):
        option = poll_with_options.options.first()
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)
        response = api_client.patch(
            f"/api/community/events/{poll_event.id}/poll/options/{option.id}/",
            data=json.dumps({"datetime": future_iso(days=200)}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert not PollVote.objects.filter(option=option).exists()
        data = response.json()
        updated = next(o for o in data["options"] if o["id"] == str(option.id))
        assert updated["yes_count"] == 0

    def test_update_no_votes_still_succeeds(
        self, api_client, auth_headers, poll_with_options, poll_event
    ):
        option = poll_with_options.options.first()
        new_datetime = future_iso(days=200)
        response = api_client.patch(
            f"/api/community/events/{poll_event.id}/poll/options/{option.id}/",
            data=json.dumps({"datetime": new_datetime}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        option.refresh_from_db()
        assert option.datetime.isoformat().startswith(new_datetime[:16])
