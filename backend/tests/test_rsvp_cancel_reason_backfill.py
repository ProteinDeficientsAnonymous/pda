import importlib
import logging
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import CancelReason, EventRSVP, RSVPStatus
from django.apps import apps
from django.utils import timezone

from tests._events import make_event, make_rsvp

pytestmark = pytest.mark.django_db

backfill = importlib.import_module("community.migrations.0137_backfill_rsvp_cancel_reason")


def _cancelled(user, cancelled_at):
    return make_rsvp(make_event(), user, RSVPStatus.CANT_GO, cancelled_at=cancelled_at)


def _audit(action, user, details=None, target_type=AuditTargetType.USER, target_id=None):
    return AuditLogEntry.objects.create(
        action=action,
        actor_label="admin",
        target_type=target_type,
        target_id=target_id or str(user.pk),
        details=details or {},
        level=logging.WARNING,
    )


def _reasons(*rsvps):
    return [EventRSVP.objects.get(pk=r.pk).cancel_reason for r in rsvps]


@pytest.mark.parametrize("action", ["user_attendance_paused", "user_paused"])
def test_marks_rsvps_a_pause_released(test_user, action):
    now = timezone.now()
    released, own = _cancelled(test_user, now), _cancelled(test_user, now)
    _audit(action, test_user, {"removed_rsvp_event_ids": [str(released.event_id)]})

    backfill.backfill_cancel_reason(apps, None)

    assert _reasons(released, own) == [CancelReason.PAUSE, CancelReason.SELF]


def test_a_later_self_cancel_on_a_released_event_stays_self(test_user):
    rsvp = _cancelled(test_user, timezone.now() + timedelta(days=2))
    _audit("user_paused", test_user, {"removed_rsvp_event_ids": [str(rsvp.event_id)]})

    backfill.backfill_cancel_reason(apps, None)

    assert _reasons(rsvp) == [CancelReason.SELF]


@pytest.mark.parametrize("action", ["user_archived", "user_self_deleted"])
def test_marks_rsvps_an_archive_released(test_user, action):
    released = _cancelled(test_user, timezone.now())
    earlier = _cancelled(test_user, timezone.now() - timedelta(days=5))
    _audit(action, test_user)

    backfill.backfill_cancel_reason(apps, None)

    assert _reasons(released, earlier) == [CancelReason.ARCHIVE, CancelReason.SELF]


def test_marks_rsvps_a_host_cancelled(test_user):
    by_host, own = _cancelled(test_user, timezone.now()), _cancelled(test_user, timezone.now())
    for rsvp, status in ((by_host, RSVPStatus.CANT_GO), (own, RSVPStatus.ATTENDING)):
        details = {"user_id": str(test_user.pk), "status": status}
        _audit("guest_rsvp_changed", test_user, details, AuditTargetType.EVENT, str(rsvp.event_id))

    backfill.backfill_cancel_reason(apps, None)

    assert _reasons(by_host, own) == [CancelReason.HOST, CancelReason.SELF]


def test_leaves_set_reasons_and_uncancelled_rows(test_user):
    host_cancel = _cancelled(test_user, timezone.now())
    EventRSVP.objects.filter(pk=host_cancel.pk).update(cancel_reason=CancelReason.HOST)
    going = make_rsvp(make_event(), test_user)

    backfill.backfill_cancel_reason(apps, None)

    assert _reasons(host_cancel, going) == [CancelReason.HOST, None]
