import pytest
from community._validation import Code
from community.models import EventRSVP, RSVPStatus
from django.utils import timezone
from users.models import NonMemberRsvpToken

from tests._asserts import assert_error_code
from tests._payment_helpers import create_paid_event, set_payment_flag
from tests._public_rsvp_helpers import make_non_member, make_official_event
from tests._public_rsvp_helpers import payload as public_payload
from tests._public_rsvp_helpers import url as public_url

RSVP_URL = "/api/community/events/{event_id}/rsvp/"


@pytest.fixture(autouse=True)
def _flag_on(db):
    """Flag-OFF behavior is covered by test_payment_confirmation_flag_off.py."""
    set_payment_flag(True)


@pytest.fixture
def paid_event(db, test_user):
    return create_paid_event(created_by=test_user)


@pytest.mark.django_db
class TestMemberRsvpPaymentGate:
    def test_attending_without_confirmation_is_rejected(self, api_client, paid_event, auth_headers):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)
        assert not EventRSVP.objects.filter(event=paid_event).exists()

    def test_attending_with_confirmation_succeeds_and_stamps(
        self, api_client, paid_event, auth_headers
    ):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=paid_event)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is not None

    def test_maybe_without_confirmation_succeeds(self, api_client, paid_event, auth_headers):
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.MAYBE, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=paid_event).paid_confirmed_at is None

    def test_confirmed_attendee_can_toggle_plus_one_without_reconfirming(
        self, api_client, paid_event, auth_headers, test_user
    ):
        paid_event.allow_plus_ones = True
        paid_event.save(update_fields=["allow_plus_ones"])
        EventRSVP.objects.create(
            event=paid_event,
            user=test_user,
            status=RSVPStatus.ATTENDING,
            paid_confirmed_at=timezone.now(),
        )
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_unconfirmed_attendee_is_gated_on_next_write(
        self, api_client, paid_event, auth_headers, test_user
    ):
        """A row seated by waitlist promotion carries no stamp and must still gate."""
        paid_event.allow_plus_ones = True
        paid_event.save(update_fields=["allow_plus_ones"])
        EventRSVP.objects.create(event=paid_event, user=test_user, status=RSVPStatus.ATTENDING)
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_confirmation_persists_across_later_status_changes(
        self, api_client, paid_event, auth_headers
    ):
        api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False, "paid_confirmed": True},
            content_type="application/json",
            **auth_headers,
        )
        stamped = EventRSVP.objects.get(event=paid_event).paid_confirmed_at
        api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.MAYBE, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=paid_event).paid_confirmed_at == stamped

    def test_free_event_needs_no_confirmation(self, api_client, paid_event, auth_headers):
        paid_event.price = ""
        paid_event.venmo_link = ""
        paid_event.save(update_fields=["price", "venmo_link"])
        response = api_client.post(
            RSVP_URL.format(event_id=paid_event.id),
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200


@pytest.fixture
def paid_public_event(db):
    return make_official_event(
        title="Paid Official Event",
        price="$10",
        venmo_link="https://venmo.com/u/host",
    )


@pytest.mark.django_db
class TestPublicSubmitPaymentGate:
    def test_new_person_attending_without_confirmation_is_rejected(
        self, api_client, paid_public_event
    ):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.ATTENDING),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_new_person_attending_with_confirmation_succeeds(self, api_client, paid_public_event):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.ATTENDING, paid_confirmed=True),
            content_type="application/json",
        )
        assert response.status_code in (200, 201)
        assert EventRSVP.objects.get(event=paid_public_event).paid_confirmed_at is not None

    def test_new_person_maybe_needs_no_confirmation(self, api_client, paid_public_event):
        response = api_client.post(
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.MAYBE),
            content_type="application/json",
        )
        assert response.status_code in (200, 201)


@pytest.mark.django_db
class TestPublicManagePaymentGate:
    def _setup(self, event, phone="+14155550199"):
        user = make_non_member(phone, "token@example.com", name="Token Holder")
        EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.MAYBE)
        return user, NonMemberRsvpToken.issue_or_extend(user).token

    def test_maybe_to_attending_without_confirmation_is_rejected(
        self, api_client, paid_public_event
    ):
        _user, token = self._setup(paid_public_event)
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)

    def test_maybe_to_attending_with_confirmation_succeeds(self, api_client, paid_public_event):
        user, token = self._setup(paid_public_event, phone="+14155550198")
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            content_type="application/json",
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=paid_public_event, user=user)
        assert rsvp.paid_confirmed_at is not None

    def test_switching_to_maybe_needs_no_confirmation(self, api_client, paid_public_event):
        user = make_non_member("+14155550197", "t2@example.com", name="Token Two")
        EventRSVP.objects.create(event=paid_public_event, user=user, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(user).token
        response = api_client.post(
            f"/api/community/public/my-rsvps/{paid_public_event.id}/?token={token}",
            {"status": RSVPStatus.MAYBE},
            content_type="application/json",
        )
        assert response.status_code == 200
