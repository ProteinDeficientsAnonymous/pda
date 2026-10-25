"""Host verify / un-verify of a guest's payment, and who may read payment status."""

from datetime import timedelta

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import Role
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._payment_helpers import create_paid_event

RSVP_URL = "/api/community/events/{event_id}/rsvp/"
PAYMENT_URL = "/api/community/events/{event_id}/rsvps/{user_id}/payment/"


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


def _verified(host) -> dict:
    """A guest who said they paid, later verified by a host."""
    now = timezone.now()
    return {
        "paid_confirmed_at": now - timedelta(hours=1),
        "payment_verified_at": now,
        "payment_verified_by": host,
    }


@pytest.mark.django_db
class TestHostRevokePayment:
    def test_unverify_keeps_the_guests_attestation(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """Un-verifying only drops the host mark; the guest's own "i paid" still stands."""
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550301", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.CANT_GO, **_verified(test_user)
        )

        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.payment_verified_at is None
        assert rsvp.payment_verified_by is None
        assert rsvp.paid_confirmed_at is not None

        response = api_client.post(
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 200, "un-verifying must not re-gate the guest"

    def test_undoing_a_host_stamped_verify_regates_and_guest_can_reconfirm(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """A mis-clicked verify on a guest who never claimed payment must fully undo."""
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550302", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.MAYBE)
        url = PAYMENT_URL.format(event_id=event.id, user_id=guest.id)
        for paid in (True, False):
            api_client.patch(
                url, {"paid_confirmed": paid}, content_type="application/json", **auth_headers
            )

        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is None
        assert rsvp.payment_verified_at is None
        assert not Notification.objects.filter(
            recipient=guest, notification_type=NotificationType.PAYMENT_REVOKED
        ).exists(), "they never claimed a payment, so there is nothing to tell them"

        rsvp_url = RSVP_URL.format(event_id=event.id)
        gated = api_client.post(
            rsvp_url,
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_headers(guest),
        )
        assert gated.status_code == 400
        assert_error_code(gated, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

        response = api_client.post(
            rsvp_url,
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=guest).paid_confirmed_at is not None

    def test_revoke_notifies_the_guest(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550303", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, **_verified(test_user)
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
        assert notification.message == (
            f"your payment for {event.title} needs attention — a host couldn't verify it."
        )

    def test_unverifying_an_unverified_rsvp_does_not_notify(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        """No host verification stood, so nothing was taken away."""
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550304", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
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
        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at is not None, "a verified guest must never be gated"
        assert rsvp.payment_verified_at is not None
        assert rsvp.payment_verified_by == test_user

    def test_verifying_keeps_the_guests_own_stamp(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550311", first_name="Guest", is_member=True
        )
        attested_at = timezone.now() - timedelta(days=1)
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, paid_confirmed_at=attested_at
        )
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        rsvp = EventRSVP.objects.get(event=event, user=guest)
        assert rsvp.paid_confirmed_at == attested_at
        assert rsvp.payment_verified_at is not None

    def test_reverifying_keeps_the_original_verifier(
        self, api_client, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550312", first_name="Guest", is_member=True
        )
        rsvp = EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, **_verified(test_user)
        )
        cohost = django_user_model.objects.create_user(
            phone_number="+14155550313", first_name="Cohost", is_member=True
        )
        event.co_hosts.add(cohost)
        api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": True},
            content_type="application/json",
            **_headers(cohost),
        )
        stored = EventRSVP.objects.get(pk=rsvp.pk)
        assert stored.payment_verified_by == test_user
        assert stored.payment_verified_at == rsvp.payment_verified_at

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
        seeded = EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, **_verified(test_user)
        )
        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            content_type="application/json",
            **_headers(guest),
        )
        assert response.status_code == 403
        rsvp = EventRSVP.objects.get(pk=seeded.pk)
        assert rsvp.payment_verified_at == seeded.payment_verified_at
        assert rsvp.payment_verified_by == test_user
        assert rsvp.paid_confirmed_at == seeded.paid_confirmed_at

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
        """A guest's own cancel keeps their confirmation."""
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
    def _guests(self, api_client, event, headers, field="paid_confirmed"):
        body = api_client.get(f"/api/community/events/{event.id}/", **headers).json()
        return {g["name"]: g[field] for g in body["guests"]}

    def _event_with_a_payer(self, host, django_user_model, phone):
        event = _paid_event(host)
        payer = django_user_model.objects.create_user(
            phone_number=phone, first_name="Payer", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=payer, status=RSVPStatus.ATTENDING, **_verified(host)
        )
        return event

    def test_host_sees_payment_status(self, api_client, auth_headers, test_user, django_user_model):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550401")
        assert self._guests(api_client, event, auth_headers)["Payer"] is True
        assert self._guests(api_client, event, auth_headers, "payment_verified")["Payer"] is True

    def test_self_attested_guest_reads_as_unverified(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        payer = django_user_model.objects.create_user(
            phone_number="+14155550411", first_name="Payer", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=payer, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
        assert self._guests(api_client, event, auth_headers)["Payer"] is True
        assert self._guests(api_client, event, auth_headers, "payment_verified")["Payer"] is False

    def test_event_manager_sees_payment_status(self, api_client, test_user, django_user_model):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550407")
        manager = django_user_model.objects.create_user(
            phone_number="+14155550408", first_name="Manager", is_member=True
        )
        manager.roles.add(
            Role.objects.create(name="event_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
        )
        assert self._guests(api_client, event, _headers(manager))["Payer"] is True

    def test_event_manager_can_mark_paid(self, api_client, test_user, django_user_model):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550409", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
        manager = django_user_model.objects.create_user(
            phone_number="+14155550410", first_name="Manager", is_member=True
        )
        manager.roles.add(
            Role.objects.create(name="event_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
        )

        response = api_client.patch(
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": True},
            content_type="application/json",
            **_headers(manager),
        )
        assert response.status_code == 200
        guests = {g["name"]: g for g in response.json()["guests"]}
        assert guests["Guest"]["paid_confirmed"] is True
        assert guests["Guest"]["payment_verified"] is True

    def test_plain_member_does_not_see_payment_status(
        self, api_client, test_user, django_user_model
    ):
        event = self._event_with_a_payer(test_user, django_user_model, "+14155550402")
        nosy = django_user_model.objects.create_user(
            phone_number="+14155550403", first_name="Nosy", is_member=True
        )
        EventRSVP.objects.create(event=event, user=nosy, status=RSVPStatus.ATTENDING)
        assert self._guests(api_client, event, _headers(nosy))["Payer"] is False
        assert self._guests(api_client, event, _headers(nosy), "payment_verified")["Payer"] is False

    def test_unverified_guest_still_reads_as_attested_to_the_host(
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
        assert self._guests(api_client, event, auth_headers, "payment_verified")["Payer"] is False
        assert self._guests(api_client, event, auth_headers)["Payer"] is True

    def test_my_paid_confirmed_survives_an_unverify(
        self, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550406", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, **_verified(test_user)
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
        assert body["my_paid_confirmed"] is True
