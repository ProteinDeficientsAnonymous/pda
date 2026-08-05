"""Host revoke of a payment confirmation, and who may read payment status."""

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, FeatureFlag, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType

from tests._asserts import assert_error_code
from tests._payment_helpers import create_paid_event, set_payment_flag

RSVP_URL = "/api/community/events/{event_id}/rsvp/"
PAYMENT_URL = "/api/community/events/{event_id}/rsvps/{user_id}/payment/"

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


@pytest.fixture(autouse=True)
def _flag_on(db):
    set_payment_flag(True)


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


@pytest.mark.django_db
class TestHostRevokePayment:
    def test_revoke_regates_the_guest(self, api_client, auth_headers, test_user, django_user_model):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550301", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event,
            user=guest,
            status=RSVPStatus.ATTENDING,
            paid_confirmed_at=timezone.now(),
        )

        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is None

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_guest_can_reconfirm_after_a_revoke(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550302", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event,
            user=guest,
            status=RSVPStatus.ATTENDING,
            paid_confirmed_at=timezone.now(),
        )
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is not None

    def test_revoke_notifies_the_guest(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550303", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event,
            user=guest,
            status=RSVPStatus.ATTENDING,
            paid_confirmed_at=timezone.now(),
        )
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        notification = Notification.objects.get(
            recipient=guest, notification_type=NotificationType.PAYMENT_REVOKED
        )
        assert event.title in notification.message

    def test_revoking_an_unpaid_rsvp_does_not_notify(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """No confirmation stood, so nothing was taken away."""
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550304", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert not Notification.objects.filter(
            recipient=guest, notification_type=NotificationType.PAYMENT_REVOKED
        ).exists()

    def test_host_can_confirm_via_patch(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550305", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=guest).paid_confirmed_at is not None

    def test_patch_does_not_change_rsvp_status(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550306", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.MAYBE, paid_confirmed_at=timezone.now()
        )
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert EventRSVP.objects.get(event=event, user=guest).status == RSVPStatus.MAYBE

    def test_non_host_cannot_revoke(self, api_client, test_user, django_user_model):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550307", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 403
        assert EventRSVP.objects.get(event=event, user=guest).paid_confirmed_at is not None

    def test_missing_rsvp_is_404(self, api_client, auth_headers, test_user, django_user_model):
        event = _paid_event(test_user)
        stranger = django_user_model.objects.create_user(
            phone_number="+14155550308", first_name="Stranger", is_member=True
        )
        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=stranger.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404

    def test_ordinary_cancel_and_rersvp_needs_no_reconfirmation(
        self, api_client, test_user, django_user_model
    ):
        """Only a host revoke re-gates; a guest's own cancel keeps their confirmation."""
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550309", first_name="Guest", is_member=True
        )
        headers = _headers(guest)
        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            content_type="application/json",
            **headers,
        )
        api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **headers,
        )
        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestPaymentStatusVisibility:
    def _guests(self, api_client, event, headers):
        body = api_client.get(f"/api/community/events/{event.id}/", **headers).json()
        return {g["name"]: g["paid_confirmed"] for g in body["guests"]}

    def _event_with_a_payer(self, host, django_user_model, phone):
        event = _paid_event(host)
        payer = django_user_model.objects.create_user(
            phone_number=phone, first_name="Payer", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=payer, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
        return event

    def test_host_sees_payment_status(self, api_client, auth_headers, test_user, django_user_model):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550401")
        assert self._guests(api_client, event, auth_headers)["Payer"] is True

    def test_plain_member_does_not_see_payment_status(
        self, api_client, test_user, django_user_model
    ):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550402")
        nosy = django_user_model.objects.create_user(
            phone_number="+14155550403", first_name="Nosy", is_member=True
        )
        EventRSVP.objects.create(event=event, user=nosy, status=RSVPStatus.ATTENDING)
        assert self._guests(api_client, event, _headers(nosy))["Payer"] is False

    def test_flag_off_hides_payment_status_from_the_host_too(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        set_payment_flag(False)
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550404")
        assert self._guests(api_client, event, auth_headers)["Payer"] is False

    def test_revoked_guest_reads_as_unpaid_to_the_host(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550405")
        payer = django_user_model.objects.get(phone_number="+14155550405")
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=payer.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert self._guests(api_client, event, auth_headers)["Payer"] is False

    def test_my_paid_confirmed_goes_false_after_a_revoke(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550406", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
        body = api_client.get(f"/api/community/events/{event.id}/", **_headers(guest)).json()
        assert body["my_paid_confirmed"] is True

        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        body = api_client.get(f"/api/community/events/{event.id}/", **_headers(guest)).json()
        assert body["my_paid_confirmed"] is False
