"""Regression tests for payment-gate bypasses caught in code review."""

import pytest
from community._validation import Code
from community._waitlist import promote_from_waitlist
from community.models import (
    Event,
    EventPoll,
    EventRSVP,
    PollAvailability,
    PollOption,
    PollVote,
    RSVPStatus,
)
from django.db import transaction
from django.utils import timezone
from notifications.models import Notification

from tests._asserts import assert_error_code
from tests._payment_helpers import create_paid_event
from tests.conftest import future_iso

RSVP_URL = "/api/community/events/{event_id}/rsvp/"


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


@pytest.mark.django_db
class TestWaitlistPromotionBypass:
    def test_unconfirmed_attending_at_capacity_joins_the_waitlist_unpaid(
        self, api_client, auth_headers, test_user, django_user_model
    ):
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
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=test_user)
        assert rsvp.status == RSVPStatus.WAITLISTED
        assert rsvp.paid_confirmed_at is None

    def test_unpaid_waitlister_is_promoted_and_told_to_pay(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user, max_attendees=1)
        seated = django_user_model.objects.create_user(
            phone_number="+14155550111", first_name="Seated", is_member=True
        )
        seat = EventRSVP.objects.create(event=event, user=seated, status=RSVPStatus.ATTENDING)
        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )

        seat.delete()
        with transaction.atomic():
            promote_from_waitlist(Event.objects.select_for_update().get(id=event.id))

        assert EventRSVP.objects.get(event=event, user=test_user).status == RSVPStatus.ATTENDING
        note = Notification.objects.get(recipient=test_user, event=event)
        assert "isn't confirmed until you pay" in note.message

    def test_promoted_unpaid_attendee_is_gated_on_next_write(
        self, api_client, auth_headers, test_user
    ):
        event = _paid_event(test_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)


@pytest.mark.django_db
class TestPaidConfirmedOnUngatedStatus:
    def test_maybe_with_paid_confirmed_does_not_bank_a_stamp(
        self, api_client, auth_headers, test_user
    ):
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
class TestPollFinalizeKeepsConfirmation:
    def test_yes_voter_with_existing_confirmation_keeps_it(
        self, api_client, auth_headers, test_user
    ):

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
    event = _paid_event(test_user)
    api_client.post(
        RSVP_URL.format(event_id=event.id),
        {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
        content_type="application/json",
        **auth_headers,
    )
    stamped = EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at
    assert timezone.is_aware(stamped)
