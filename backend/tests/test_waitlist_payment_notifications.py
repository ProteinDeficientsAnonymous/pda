"""Tests for payment-aware waitlist promotion notifications and emails."""

import pytest
from community._event_helpers import promote_from_waitlist
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone

from tests._payment_helpers import create_paid_event, set_payment_flag

RSVP_URL = "/api/community/events/{event_id}/rsvp/"


@pytest.fixture(autouse=True)
def _flag_on(db):
    set_payment_flag(True)


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


@pytest.mark.django_db
class TestWaitlistPromotionPaymentMessaging:
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
