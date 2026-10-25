from datetime import timedelta

import pytest
from community._event_nonmember_removal import guard_or_remove_ineligible_non_members
from community.models import Event, EventRSVP, RSVPStatus
from django.utils import timezone
from users.models import User

from tests.conftest import future_iso

LONG_AGO = timezone.now() - timedelta(days=30)


@pytest.fixture
def event(test_user):
    return Event.objects.create(
        title="Digest Event",
        start_datetime=future_iso(days=14),
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def rsvp(event, test_user):
    return EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)


def _backdate(rsvp: EventRSVP) -> EventRSVP:
    EventRSVP.objects.filter(pk=rsvp.pk).update(status_changed_at=LONG_AGO)
    rsvp.refresh_from_db()
    return rsvp


def _assert_stamped(rsvp: EventRSVP) -> None:
    rsvp.refresh_from_db()
    assert rsvp.status_changed_at > LONG_AGO


def _assert_untouched(rsvp: EventRSVP) -> None:
    rsvp.refresh_from_db()
    assert rsvp.status_changed_at == LONG_AGO


class TestStatusChangedAt:
    def test_set_on_create(self, rsvp):
        rsvp.refresh_from_db()
        assert timezone.now() - rsvp.status_changed_at < timedelta(minutes=1)

    @pytest.mark.parametrize("update_fields", [None, ["status"]])
    def test_set_on_status_change(self, rsvp, update_fields):
        _backdate(rsvp)
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.save(update_fields=update_fields)
        _assert_stamped(rsvp)

    def test_set_on_change_after_external_update_and_refresh(self, rsvp):
        EventRSVP.objects.filter(pk=rsvp.pk).update(
            status=RSVPStatus.CANT_GO, status_changed_at=LONG_AGO
        )
        rsvp.refresh_from_db()
        rsvp.status = RSVPStatus.ATTENDING
        rsvp.save()
        _assert_stamped(rsvp)

    def test_set_on_status_change_when_status_loaded_lazily(self, rsvp):
        _backdate(rsvp)
        deferred = EventRSVP.objects.defer("status").get(pk=rsvp.pk)
        assert deferred.status == RSVPStatus.ATTENDING
        deferred.status = RSVPStatus.CANT_GO
        deferred.save()
        _assert_stamped(rsvp)

    def test_deferred_status_stamped_only_when_in_update_fields(self, rsvp):
        _backdate(rsvp)
        deferred = EventRSVP.objects.only("id").get(pk=rsvp.pk)
        deferred.has_plus_one = True
        deferred.save(update_fields=["has_plus_one"])
        _assert_untouched(rsvp)

        deferred = EventRSVP.objects.only("id").get(pk=rsvp.pk)
        deferred.status = RSVPStatus.CANT_GO
        deferred.save(update_fields=["status"])
        _assert_stamped(rsvp)

    def test_deferred_status_set_then_plain_save_is_stamped(self, rsvp):
        _backdate(rsvp)
        deferred = EventRSVP.objects.only("id").get(pk=rsvp.pk)
        deferred.status = RSVPStatus.CANT_GO
        deferred.save()
        _assert_stamped(rsvp)

    def test_status_change_excluded_from_update_fields_is_not_stamped(self, rsvp):
        _backdate(rsvp)
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.has_plus_one = True
        rsvp.save(update_fields=["has_plus_one"])
        _assert_untouched(rsvp)
        assert rsvp.status == RSVPStatus.ATTENDING

    @pytest.mark.parametrize("use_update_fields", [False, True])
    def test_untouched_by_non_status_saves(self, rsvp, use_update_fields):
        _backdate(rsvp)
        now = timezone.now()
        for field, value in (
            ("paid_confirmed_at", now),
            ("checked_in_at", now),
            ("has_plus_one", True),
        ):
            setattr(rsvp, field, value)
            rsvp.save(update_fields=[field] if use_update_fields else None)
            _assert_untouched(rsvp)

    def test_second_save_after_status_change_keeps_value(self, rsvp):
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.save()
        _backdate(rsvp)
        rsvp.has_plus_one = True
        rsvp.save()
        _assert_untouched(rsvp)

    def test_set_by_nonmember_bulk_removal(self, event):
        guest = User.objects.create_user(phone_number="+12025558400", password="x", is_member=False)
        row = _backdate(
            EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
        )

        assert len(guard_or_remove_ineligible_non_members(event, force=True)) == 1

        _assert_stamped(row)
        assert row.status == RSVPStatus.REMOVED
