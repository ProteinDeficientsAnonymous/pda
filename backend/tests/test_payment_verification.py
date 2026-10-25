import importlib
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import EventRSVP, RSVPStatus
from django.apps import apps
from django.utils import timezone

from tests._payment_helpers import create_paid_event

pytestmark = pytest.mark.django_db

backfill = importlib.import_module("community.migrations.0114_backfill_eventrsvp_payment_verified")


@pytest.fixture
def event(test_user):
    return create_paid_event(created_by=test_user)


@pytest.fixture
def guest(django_user_model):
    return django_user_model.objects.create_user(
        phone_number="+14155550501", first_name="Guest", is_member=True
    )


def _log(action, actor, event, guest, at, **details):
    entry = AuditLogEntry.objects.create(
        action=action,
        actor=actor,
        actor_label=actor.full_name if actor else "anonymous",
        target_type=AuditTargetType.EVENT,
        target_id=str(event.id),
        details={"user_id": str(guest.id), **details},
        level=20,
    )
    AuditLogEntry.objects.filter(pk=entry.pk).update(created_at=at)
    return at


class TestBackfill:
    @pytest.fixture
    def rsvp(self, event, guest):
        rsvp = EventRSVP.objects.create(
            event=event, user=guest, status=RSVPStatus.ATTENDING, paid_confirmed_at=timezone.now()
        )
        EventRSVP.objects.filter(pk=rsvp.pk).update(created_at=timezone.now() - timedelta(days=5))
        return rsvp

    def _run(self, rsvp):
        backfill.backfill_payment_verified(apps, None)
        rsvp.refresh_from_db()
        return rsvp

    def test_latest_set_paid_verifies_with_its_actor_and_time(self, rsvp, event, guest, test_user):
        at = _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
            was_paid=False,
        )

        rsvp = self._run(rsvp)

        assert rsvp.payment_verified_at == at
        assert rsvp.payment_verified_by == test_user

    def test_host_stamped_row_keeps_the_stamp_as_its_verified_time(
        self, rsvp, event, guest, test_user
    ):
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
            was_paid=False,
            paid_confirmed_at=rsvp.paid_confirmed_at.isoformat(),
        )

        rsvp = self._run(rsvp)

        assert rsvp.payment_verified_at == rsvp.paid_confirmed_at

    def test_self_attested_row_verifies_at_the_entry_time(self, rsvp, event, guest, test_user):
        at = _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
            was_paid=True,
            paid_confirmed_at=rsvp.paid_confirmed_at.isoformat(),
        )

        assert self._run(rsvp).payment_verified_at == at

    def test_original_payload_shape_counts(self, rsvp, event, guest, test_user):
        """The first release logged only user_id + the requested paid_confirmed."""
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
        )

        assert self._run(rsvp).payment_verified_by == test_user

    def test_later_revoke_wins(self, rsvp, event, guest, test_user):
        now = timezone.now()
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            now - timedelta(days=2),
            paid_confirmed=True,
        )
        _log(
            "guest_payment_revoked",
            test_user,
            event,
            guest,
            now - timedelta(days=1),
            paid_confirmed=False,
        )

        assert self._run(rsvp).payment_verified_at is None

    def test_latest_redundant_clear_is_not_a_verification(self, rsvp, event, guest, test_user):
        now = timezone.now()
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            now - timedelta(days=2),
            paid_confirmed=True,
        )
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            now - timedelta(days=1),
            paid_confirmed=False,
        )

        assert self._run(rsvp).payment_verified_at is None

    def test_rsvp_recreated_after_the_entry_is_skipped(self, rsvp, event, guest, test_user):
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=10),
            paid_confirmed=True,
        )

        assert self._run(rsvp).payment_verified_at is None

    def test_unstamped_rsvp_is_skipped(self, rsvp, event, guest, test_user):
        EventRSVP.objects.filter(pk=rsvp.pk).update(paid_confirmed_at=None)
        _log(
            "guest_payment_changed",
            test_user,
            event,
            guest,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
        )

        assert self._run(rsvp).payment_verified_at is None

    def test_other_guests_entries_do_not_leak(self, rsvp, event, test_user, django_user_model):
        other = django_user_model.objects.create_user(
            phone_number="+14155550502", first_name="Other", is_member=True
        )
        _log(
            "guest_payment_changed",
            test_user,
            event,
            other,
            timezone.now() - timedelta(days=1),
            paid_confirmed=True,
        )

        assert self._run(rsvp).payment_verified_at is None
