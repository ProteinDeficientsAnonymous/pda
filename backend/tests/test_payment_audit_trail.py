import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone

from tests._payment_helpers import create_paid_event, set_payment_flag
from tests._public_rsvp_helpers import make_official_event
from tests._public_rsvp_helpers import payload as public_payload
from tests._public_rsvp_helpers import url as public_url

RSVP_URL = "/api/community/events/{event_id}/rsvp/"
HOST_RSVP_URL = "/api/community/events/{event_id}/rsvps/{user_id}/rsvp/"
PAYMENT_URL = "/api/community/events/{event_id}/rsvps/{user_id}/payment/"


@pytest.fixture(autouse=True)
def _flag_on(db):
    set_payment_flag(True)


@pytest.fixture
def commit(django_capture_on_commit_callbacks, fake_email_sender):
    """audit_log persists via transaction.on_commit, which the test transaction never fires.

    fake_email_sender because executing the callbacks also fires queued sends.
    """

    def run(fn):
        with django_capture_on_commit_callbacks(execute=True):
            return fn()

    return run


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


def _entry(action: str) -> AuditLogEntry:
    return AuditLogEntry.objects.filter(action=action).latest("created_at")


def _post(commit, api_client, url, body, headers=None):
    return commit(
        lambda: api_client.post(url, body, content_type="application/json", **(headers or {}))
    )


def _patch(commit, api_client, url, body, headers=None):
    return commit(
        lambda: api_client.patch(url, body, content_type="application/json", **(headers or {}))
    )


@pytest.mark.django_db
class TestMemberRsvpPaymentAudit:
    def test_confirming_payment_is_audited(self, commit, api_client, auth_headers, test_user):
        event = _paid_event(test_user)
        _post(
            commit,
            api_client,
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            auth_headers,
        )

        entry = _entry("rsvp_changed")
        assert entry.actor_id == test_user.pk
        assert entry.target_type == AuditTargetType.EVENT
        assert entry.target_id == str(event.id)
        assert entry.details["paid_confirmed"] is True
        assert entry.details["paid_confirmed_at"] is not None

    def test_unpaid_rsvp_is_audited_as_unpaid(self, commit, api_client, auth_headers, test_user):
        event = _paid_event(test_user)
        _post(
            commit,
            api_client,
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.MAYBE},
            auth_headers,
        )

        entry = _entry("rsvp_changed")
        assert entry.details["paid_confirmed"] is False
        assert entry.details["paid_confirmed_at"] is None

    def test_paid_confirmed_on_an_ungated_status_is_not_audited_as_paid(
        self, commit, api_client, auth_headers, test_user
    ):
        """maybe never banks a stamp, so the trail must not claim they paid."""
        event = _paid_event(test_user)
        _post(
            commit,
            api_client,
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.MAYBE, "paid_confirmed": True},
            auth_headers,
        )

        assert _entry("rsvp_changed").details["paid_confirmed"] is False

    def test_audited_stamp_matches_the_stored_row(
        self, commit, api_client, auth_headers, test_user
    ):
        event = _paid_event(test_user)
        _post(
            commit,
            api_client,
            RSVP_URL.format(event_id=event.id),
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            auth_headers,
        )

        stored = EventRSVP.objects.get(event=event, user=test_user).paid_confirmed_at
        assert _entry("rsvp_changed").details["paid_confirmed_at"] == stored.isoformat()


@pytest.mark.django_db
class TestHostPaymentChangeAudit:
    def _guest(self, django_user_model, event, **rsvp_fields):
        guest = django_user_model.objects.create_user(
            phone_number="+14155550142", first_name="Guest", is_member=True
        )
        EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, **rsvp_fields
        )
        return guest

    def test_revoking_is_audited_with_the_transition(
        self, commit, api_client, auth_headers, test_user, django_user_model
    ):
        """The row is left with no stamp, so only the audit row records that they had paid."""
        event = _paid_event(test_user)
        guest = self._guest(django_user_model, event, paid_confirmed_at=timezone.now())

        _patch(
            commit,
            api_client,
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            auth_headers,
        )

        entry = _entry("guest_payment_revoked")
        assert entry.actor_id == test_user.pk, "the host who revoked must be recorded"
        assert entry.details["user_id"] == str(guest.id)
        assert entry.details["was_paid"] is True
        assert entry.details["paid_confirmed"] is False
        assert entry.details["paid_confirmed_at"] is None
        assert not AuditLogEntry.objects.filter(action="guest_payment_changed").exists(), (
            "a real revoke must not also log under the generic action name"
        )

    def test_confirming_is_audited(
        self, commit, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = self._guest(django_user_model, event)

        _patch(
            commit,
            api_client,
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": True},
            auth_headers,
        )

        entry = _entry("guest_payment_changed")
        assert entry.details["was_paid"] is False
        assert entry.details["paid_confirmed"] is True
        assert entry.details["paid_confirmed_at"] is not None

    def test_redundant_revoke_records_no_prior_payment(
        self, commit, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = self._guest(django_user_model, event)

        _patch(
            commit,
            api_client,
            PAYMENT_URL.format(event_id=event.id, user_id=guest.id),
            {"paid_confirmed": False},
            auth_headers,
        )

        assert _entry("guest_payment_changed").details["was_paid"] is False
        assert not AuditLogEntry.objects.filter(action="guest_payment_revoked").exists(), (
            "a no-op on an unpaid guest must not log as a revoke"
        )

    def test_host_seating_a_guest_audits_the_stamp(
        self, commit, api_client, auth_headers, test_user, django_user_model
    ):
        event = _paid_event(test_user)
        guest = django_user_model.objects.create_user(
            phone_number="+14155550143", first_name="Cash", is_member=True
        )

        _post(
            commit,
            api_client,
            HOST_RSVP_URL.format(event_id=event.id, user_id=guest.id),
            {"status": RSVPStatus.ATTENDING, "paid_confirmed": True},
            auth_headers,
        )

        entry = _entry("guest_rsvp_changed")
        assert entry.details["paid_confirmed"] is True
        assert entry.details["paid_confirmed_at"] is not None


@pytest.mark.django_db
class TestPublicRsvpPaymentAudit:
    @pytest.fixture
    def paid_public_event(self, db):
        return make_official_event(
            title="Paid Official Event",
            price="$10",
            venmo_link="https://venmo.com/u/host",
        )

    def test_new_person_confirming_payment_is_audited(self, commit, api_client, paid_public_event):
        _post(
            commit,
            api_client,
            public_url(paid_public_event),
            public_payload(status=RSVPStatus.ATTENDING, paid_confirmed=True),
        )

        entry = _entry("public_rsvp_created")
        assert entry.details["paid_confirmed"] is True
        assert entry.details["paid_confirmed_at"] is not None
