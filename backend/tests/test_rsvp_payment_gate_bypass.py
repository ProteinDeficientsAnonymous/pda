"""Regression tests for the payment-gate bypasses found in review of PR #1213."""

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
    def test_promoted_attendee_is_gated_on_their_next_write(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """Promotion seats an unconfirmed row; the gate must still catch them."""
        event = _paid_event(test_user, max_attendees=1)
        seated = django_user_model.objects.create_user(
            phone_number="+14155550111", first_name="Seated", is_member=True
        )
        EventRSVP.objects.create(event=event, user=seated, status=RSVPStatus.ATTENDING)

        # At capacity, an unconfirmed attending request is waitlisted, not gated.
        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        mine = EventRSVP.objects.get(event=event, user=test_user)
        assert mine.status == RSVPStatus.WAITLISTED
        assert mine.paid_confirmed_at is None

        EventRSVP.objects.filter(event=event, user=seated).delete()
        promote_from_waitlist(event)
        mine.refresh_from_db()
        assert mine.status == RSVPStatus.ATTENDING
        assert mine.paid_confirmed_at is None

        # The promoted-but-unpaid attendee is re-prompted on their next write.
        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

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
