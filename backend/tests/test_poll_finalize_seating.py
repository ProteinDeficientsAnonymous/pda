"""Finalize seats yes-voters through the shared RSVP write path (Issue 1238)."""

import json

import pytest
from community._event_helpers import promote_from_waitlist
from community.models import (
    Event,
    EventPoll,
    EventRSVP,
    PollAvailability,
    PollOption,
    PollVote,
    RSVPStatus,
)
from users.models import User

from tests.conftest import future_iso


def _finalize(api_client, headers, event, option):
    return api_client.post(
        f"/api/community/events/{event.id}/poll/finalize/",
        data=json.dumps({"winning_option_id": str(option.id)}),
        content_type="application/json",
        **headers,
    )


def _vote_yes(option, user):
    return PollVote.objects.create(option=option, user=user, availability=PollAvailability.YES)


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="RSVP Poll Event",
        datetime_tbd=True,
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def rsvp_poll(db, rsvp_event, test_user):
    poll = EventPoll.objects.create(event=rsvp_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    return poll


@pytest.fixture
def no_rsvp_event(db, test_user):
    return Event.objects.create(
        title="No RSVP Poll Event",
        datetime_tbd=True,
        created_by=test_user,
    )


@pytest.fixture
def no_rsvp_poll(db, no_rsvp_event, test_user):
    poll = EventPoll.objects.create(event=no_rsvp_event, created_by=test_user)
    PollOption.objects.create(poll=poll, datetime=future_iso(days=120), display_order=0)
    return poll


@pytest.fixture
def other_user(db):
    return User.objects.create_user(phone_number="+12025550202", first_name="Other")


@pytest.mark.django_db
class TestFinalizeSeating:
    def test_seats_yes_voter_as_attending(
        self, api_client, auth_headers, rsvp_event, rsvp_poll, test_user
    ):
        option = rsvp_poll.options.first()
        _vote_yes(option, test_user)

        assert _finalize(api_client, auth_headers, rsvp_event, option).status_code == 200
        assert EventRSVP.objects.get(event=rsvp_event, user=test_user).status == (
            RSVPStatus.ATTENDING
        )

    def test_capacity_is_respected_overflow_waitlisted(
        self, api_client, auth_headers, rsvp_event, rsvp_poll
    ):
        rsvp_event.max_attendees = 3
        rsvp_event.save(update_fields=["max_attendees"])
        option = rsvp_poll.options.first()
        for i in range(5):
            voter = User.objects.create_user(phone_number=f"+1202555{1000 + i}", first_name=f"V{i}")
            _vote_yes(option, voter)

        assert _finalize(api_client, auth_headers, rsvp_event, option).status_code == 200
        assert EventRSVP.objects.filter(event=rsvp_event, status=RSVPStatus.ATTENDING).count() == 3
        assert EventRSVP.objects.filter(event=rsvp_event, status=RSVPStatus.WAITLISTED).count() == 2

    def test_waitlisted_voter_is_promoted_when_a_seat_frees(
        self, api_client, auth_headers, rsvp_event, rsvp_poll
    ):
        rsvp_event.max_attendees = 1
        rsvp_event.save(update_fields=["max_attendees"])
        option = rsvp_poll.options.first()
        seated = User.objects.create_user(phone_number="+12025557001", first_name="Seated")
        waiting = User.objects.create_user(phone_number="+12025557002", first_name="Waiting")
        _vote_yes(option, seated)
        _vote_yes(option, waiting)
        _finalize(api_client, auth_headers, rsvp_event, option)

        seated_rsvp = EventRSVP.objects.get(event=rsvp_event, user=seated)
        assert seated_rsvp.status == RSVPStatus.ATTENDING
        seated_rsvp.delete()

        promote_from_waitlist(rsvp_event)
        assert EventRSVP.objects.get(event=rsvp_event, user=waiting).status == RSVPStatus.ATTENDING

    def test_existing_plus_one_is_preserved(
        self, api_client, auth_headers, rsvp_event, rsvp_poll, test_user
    ):
        rsvp_event.allow_plus_ones = True
        rsvp_event.save(update_fields=["allow_plus_ones"])
        option = rsvp_poll.options.first()
        EventRSVP.objects.create(
            event=rsvp_event, user=test_user, status=RSVPStatus.MAYBE, has_plus_one=True
        )
        _vote_yes(option, test_user)

        _finalize(api_client, auth_headers, rsvp_event, option)
        rsvp = EventRSVP.objects.get(event=rsvp_event, user=test_user)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.has_plus_one is True

    def test_cancelled_rsvp_is_not_resurrected(
        self, api_client, auth_headers, rsvp_event, rsvp_poll, test_user
    ):
        option = rsvp_poll.options.first()
        EventRSVP.objects.create(event=rsvp_event, user=test_user, status=RSVPStatus.CANT_GO)
        _vote_yes(option, test_user)

        assert _finalize(api_client, auth_headers, rsvp_event, option).status_code == 200
        assert EventRSVP.objects.get(event=rsvp_event, user=test_user).status == RSVPStatus.CANT_GO

    def test_rsvp_disabled_event_seats_nobody(
        self, api_client, auth_headers, no_rsvp_event, no_rsvp_poll, test_user
    ):
        option = no_rsvp_poll.options.first()
        _vote_yes(option, test_user)

        assert _finalize(api_client, auth_headers, no_rsvp_event, option).status_code == 200
        assert not EventRSVP.objects.filter(event=no_rsvp_event).exists()

    def test_non_yes_voters_are_not_seated(
        self, api_client, auth_headers, rsvp_event, rsvp_poll, other_user
    ):
        option = rsvp_poll.options.first()
        PollVote.objects.create(option=option, user=other_user, availability=PollAvailability.NO)

        _finalize(api_client, auth_headers, rsvp_event, option)
        assert not EventRSVP.objects.filter(event=rsvp_event, user=other_user).exists()
