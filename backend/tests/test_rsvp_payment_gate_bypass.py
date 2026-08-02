"""Regression tests for payment-gate bypasses caught in code review."""

import pytest
from community._event_helpers import promote_from_waitlist
from community._validation import Code
from community.models import (
    Event,
    EventRSVP,
    EventStatus,
    FeatureFlag,
    FeatureFlagState,
    PageVisibility,
    RSVPStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.models import NotificationType

from tests._asserts import assert_error_code
from tests.conftest import future_iso

RSVP_URL = "/api/community/events/{event_id}/rsvp/"

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


@pytest.fixture(autouse=True)
def _flag_on(db):
    FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})


def _paid_event(creator, **overrides) -> Event:
    base = {
        "title": "Paid Event",
        "start_datetime": future_iso(days=10),
        "end_datetime": future_iso(days=10, hours=2),
        "rsvp_enabled": True,
        "status": EventStatus.ACTIVE,
        "visibility": PageVisibility.PUBLIC,
        "price": "$10",
        "venmo_link": "https://venmo.com/u/host",
        "created_by": creator,
    }
    base.update(overrides)
    return Event.objects.create(**base)


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

    def test_confirmed_attending_at_capacity_waitlists_and_promotes_without_regating(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """A confirmed request that lands on the waitlist stays confirmed
        through promotion — the stamp isn't lost by the capacity detour."""
        event = _paid_event(test_user, max_attendees=1)
        seated = django_user_model.objects.create_user(
            phone_number="+14155550111", first_name="Seated", is_member=True
        )
        EventRSVP.objects.create(event=event, user=seated, status=RSVPStatus.ATTENDING)

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        mine = EventRSVP.objects.get(event=event, user=test_user)
        assert mine.status == RSVPStatus.WAITLISTED
        assert mine.paid_confirmed_at is not None
        stamped = mine.paid_confirmed_at

        EventRSVP.objects.filter(event=event, user=seated).delete()
        promote_from_waitlist(event)
        mine.refresh_from_db()
        assert mine.status == RSVPStatus.ATTENDING
        assert mine.paid_confirmed_at == stamped

    def test_promotion_notification_warns_about_payment(self, test_user, django_user_model):
        from notifications.models import Notification

        event = _paid_event(test_user, max_attendees=1)
        waiting = django_user_model.objects.create_user(
            phone_number="+14155550112", first_name="Waiting", is_member=True
        )
        EventRSVP.objects.create(event=event, user=waiting, status=RSVPStatus.WAITLISTED)
        promote_from_waitlist(event)

        message = Notification.objects.get(recipient=waiting).message
        assert "isn't confirmed until you pay" in message

    def test_free_event_promotion_keeps_the_plain_message(self, test_user, django_user_model):
        from notifications.models import Notification

        event = _paid_event(test_user, max_attendees=1, price="", venmo_link="")
        waiting = django_user_model.objects.create_user(
            phone_number="+14155550113", first_name="Waiting", is_member=True
        )
        EventRSVP.objects.create(event=event, user=waiting, status=RSVPStatus.WAITLISTED)
        promote_from_waitlist(event)

        message = Notification.objects.get(recipient=waiting).message
        assert "pay" not in message

    def test_already_paid_promoted_user_is_not_told_to_pay(self, test_user, django_user_model):
        from notifications.models import Notification

        event = _paid_event(test_user, max_attendees=1)
        paid = django_user_model.objects.create_user(
            phone_number="+14155550114", first_name="Paid", is_member=True
        )
        EventRSVP.objects.create(
            event=event,
            user=paid,
            status=RSVPStatus.WAITLISTED,
            paid_confirmed_at=timezone.now(),
        )
        promote_from_waitlist(event)

        message = Notification.objects.get(recipient=paid).message
        assert "isn't confirmed until you pay" not in message

    def test_mixed_promotion_tells_only_the_unpaid_user_to_pay(self, test_user, django_user_model):
        from notifications.models import Notification

        event = _paid_event(test_user, max_attendees=2)
        paid = django_user_model.objects.create_user(
            phone_number="+14155550115", first_name="Paid", is_member=True
        )
        unpaid = django_user_model.objects.create_user(
            phone_number="+14155550116", first_name="Unpaid", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=paid, status=RSVPStatus.WAITLISTED, paid_confirmed_at=timezone.now()
        )
        EventRSVP.objects.create(event=event, user=unpaid, status=RSVPStatus.WAITLISTED)
        promote_from_waitlist(event)

        assert "until you pay" not in Notification.objects.get(recipient=paid).message
        assert "until you pay" in Notification.objects.get(recipient=unpaid).message


@pytest.mark.django_db
class TestPollFinalizeSendsNoWaitlistNotification:
    def test_seating_yes_voters_does_not_notify(self, api_client, auth_headers, test_user):
        """Poll finalize seats voters directly; it is not a waitlist promotion."""
        from community.models import EventPoll, PollAvailability, PollOption, PollVote
        from notifications.models import Notification

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
        assert not Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.WAITLIST_PROMOTED
        ).exists()


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
class TestListSerializerPaymentParity:
    def _list(self, api_client, **headers):
        return api_client.get("/api/community/events/", **headers).json()

    def _find(self, body, event):
        return next(item for item in body if item["id"] == str(event.id))

    def test_anon_sees_payment_links_in_list_for_eligible_event(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        row = self._find(self._list(api_client), event)
        assert row["venmo_link"] == "https://venmo.com/u/host"

    def test_list_and_detail_agree_for_anon(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        row = self._find(self._list(api_client), event)
        detail = api_client.get(f"/api/community/events/{event.id}/").json()
        assert row["venmo_link"] == detail["venmo_link"]

    def test_anon_does_not_see_payment_links_in_list_for_community_event(
        self, api_client, test_user
    ):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.COMMUNITY)
        row = self._find(self._list(api_client), event)
        assert row["venmo_link"] == ""

    def test_anon_still_does_not_see_other_links_in_list(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(
            test_user,
            event_type=EventType.OFFICIAL,
            whatsapp_link="https://chat.whatsapp.com/abc",
        )
        row = self._find(self._list(api_client), event)
        assert row["whatsapp_link"] == ""


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


@pytest.mark.django_db
class TestPaymentLinkVisibilityFlagGate:
    """can_see_payment_details must not widen anon access while the gate itself is off."""

    def test_flag_off_anon_does_not_see_payment_links_even_when_public_rsvp_eligible(
        self, api_client, test_user
    ):
        from community.models import EventType

        FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": False})
        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.json()["venmo_link"] == ""

    def test_flag_on_anon_sees_payment_links_when_public_rsvp_eligible(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.json()["venmo_link"] == "https://venmo.com/u/host"

    def test_flag_off_member_still_sees_own_payment_links(
        self, api_client, auth_headers, test_user
    ):
        FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": False})
        event = _paid_event(test_user)
        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.json()["venmo_link"] == "https://venmo.com/u/host"


@pytest.mark.django_db
class TestPollFinalizeDoesNotBypassGate:
    def test_yes_voter_seated_unconfirmed_is_gated_on_next_write(
        self, api_client, auth_headers, test_user
    ):
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
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is None

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

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
class TestHostRsvpPaymentConfirmation:
    def test_host_can_stamp_confirmation_when_seating_a_guest(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550120", first_name="Guest", is_member=True
        )
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvps/{guest.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is not None

        # The guest's own next write is not re-gated: the host already confirmed it.
        guest_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(guest).access_token}"
        }
        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **guest_headers,
        )
        assert response.status_code == 200

    def test_host_seating_without_confirmation_leaves_guest_gated(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550121", first_name="Guest", is_member=True
        )
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvps/{guest.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is None


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
