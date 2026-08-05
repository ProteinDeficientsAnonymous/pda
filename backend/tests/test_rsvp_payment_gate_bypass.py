"""Regression tests for payment-gate bypasses caught in code review."""

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone

from tests._asserts import assert_error_code
from tests._payment_helpers import create_paid_event, set_payment_flag
from tests.conftest import future_iso

RSVP_URL = "/api/community/events/{event_id}/rsvp/"


@pytest.fixture(autouse=True)
def _flag_on(db):
    set_payment_flag(True)


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


@pytest.mark.django_db
class TestWaitlistPromotionBypass:
    def test_unconfirmed_attending_at_capacity_is_rejected_before_waitlisting(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """The gate must check the requested status, not the capacity-resolved
        one — otherwise an unconfirmed request queues as an unconfirmed
        waitlist row that later gets promoted with no gate ever having run."""
        event = _paid_event(test_user, max_attendees=1)
        seated = django_user_model.objects.create_user(
            phone_number="+14155550111", first_name="Seated", is_member=True
        )
        EventRSVP.objects.create(event=event, user=seated, status=RSVPStatus.ATTENDING)

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)
        assert not EventRSVP.objects.filter(event=event, user=test_user).exists()


@pytest.mark.django_db
class TestPaidConfirmedOnUngatedStatus:
    def test_maybe_with_paid_confirmed_does_not_bank_a_stamp(
        self, api_client, auth_headers, test_user
    ):
        """paid_confirmed on an ungated status must not pre-authorize a later attending."""
        event = _paid_event(test_user)
        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.MAYBE, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at is None

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_cant_go_with_paid_confirmed_does_not_bank_a_stamp(
        self, api_client, auth_headers, test_user
    ):
        event = _paid_event(test_user)
        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.CANT_GO, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at is None

    def test_a_real_confirmation_still_stamps_and_persists(
        self, api_client, auth_headers, test_user
    ):
        event = _paid_event(test_user)
        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        stamped = EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at
        assert stamped is not None

        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
            **auth_headers,
        )
        assert EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at == stamped


@pytest.mark.django_db
class TestPollFinalizeDoesNotBypassGate:
    def test_unpaid_yes_voter_is_waitlisted_not_seated(self, api_client, auth_headers, test_user):
        """Finalize routes through the shared RSVP path, so an unpaid voter is
        waitlisted with a path to confirm — never seated unconfirmed."""
        from community.models import EventPoll, PollAvailability, PollOption, PollVote

        event = _paid_event(test_user, datetime_tbd=True)
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        option = PollOption.objects.create(poll=poll, datetime=future_iso(days=120))
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)

        response = api_client.post(
            f"/api/community/events/{event.id}/poll/finalize/",
            {"winning_option_id": str(option.id)},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=test_user)
        assert rsvp.status == RSVPStatus.WAITLISTED
        assert rsvp.paid_confirmed_at is None

    def test_waitlisted_voter_is_seated_once_they_confirm_payment(
        self, api_client, auth_headers, test_user
    ):
        from community.models import EventPoll, PollAvailability, PollOption, PollVote

        event = _paid_event(test_user, datetime_tbd=True)
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        option = PollOption.objects.create(poll=poll, datetime=future_iso(days=120))
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)
        api_client.post(
            f"/api/community/events/{event.id}/poll/finalize/",
            {"winning_option_id": str(option.id)},
            content_type="application/json",
            **auth_headers,
        )

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=test_user)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is not None

    def test_yes_voter_with_existing_confirmation_keeps_it(
        self, api_client, auth_headers, test_user
    ):
        from community.models import EventPoll, PollAvailability, PollOption, PollVote

        event = _paid_event(test_user, datetime_tbd=True)
        EventRSVP.objects.create(
            event=event,
            user=test_user,
            status=RSVPStatus.MAYBE,
            paid_confirmed_at=timezone.now(),
        )
        poll = EventPoll.objects.create(event=event, created_by=test_user)
        option = PollOption.objects.create(poll=poll, datetime=future_iso(days=120))
        PollVote.objects.create(option=option, user=test_user, availability=PollAvailability.YES)

        api_client.post(
            f"/api/community/events/{event.id}/poll/finalize/",
            {"winning_option_id": str(option.id)},
            content_type="application/json",
            **auth_headers,
        )
        rsvp = EventRSVP.objects.get(event=event, user=test_user)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is not None


@pytest.mark.django_db
class TestNoOpEarlyReturnStillStamps:
    def test_confirming_an_already_seated_unconfirmed_row_persists_the_stamp(
        self, api_client, auth_headers, test_user
    ):
        """An unconfirmed attending row (e.g. from waitlist promotion) confirmed
        via the same status/plus-one must still get the stamp written — the
        unchanged-state early return must not discard it."""
        event = _paid_event(test_user)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at is not None


@pytest.mark.django_db
def test_stamp_is_a_real_datetime(api_client, auth_headers, test_user):
    """Guards against asserting on a truthy ISO string instead of a datetime."""
    event = _paid_event(test_user)
    api_client.post(
        RSVP_URL.format(event_id=event.id),
        {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
        content_type="application/json",
        **auth_headers,
    )
    stamped = EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at
    assert timezone.is_aware(stamped)
