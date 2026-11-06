import importlib
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import JoinRequestStatus
from django.apps import apps

from tests._tentative_helpers import open_official_event, tentative_user_with_rsvp

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db

backfill = importlib.import_module(
    "community.migrations.0126_backfill_joinrequest_approved_via_event"
)


def _legacy_auto_approved(join_request, event, vettor):
    user = tentative_user_with_rsvp(join_request, event, vettor)
    join_request.status = JoinRequestStatus.APPROVED
    join_request.tentative_at = join_request.submitted_at
    join_request.approved_at = join_request.submitted_at + timedelta(hours=1)
    join_request.save()
    entry = AuditLogEntry.objects.create(
        action="attendance_marked",
        actor=event.created_by,
        target_type=AuditTargetType.EVENT,
        target_id=str(event.id),
        details={"user_id": str(user.pk), "attendance": "attended", "for_plus_one": False},
        level=20,
    )
    AuditLogEntry.objects.filter(pk=entry.pk).update(
        created_at=join_request.approved_at + timedelta(seconds=1)
    )
    return user


def test_backfill_matches_the_check_in_logged_at_approval(
    sample_join_request, vettor_user, open_official_event
):
    _legacy_auto_approved(sample_join_request, open_official_event, vettor_user)
    backfill.backfill_approved_via_event(apps, None)
    sample_join_request.refresh_from_db()
    assert sample_join_request.approved_via_event == open_official_event


def test_backfill_skips_manual_approvals(sample_join_request, vettor_user, open_official_event):
    _legacy_auto_approved(sample_join_request, open_official_event, vettor_user)
    AuditLogEntry.objects.create(
        action="join_request_approved",
        actor=vettor_user,
        target_type=AuditTargetType.JOIN_REQUEST,
        target_id=str(sample_join_request.id),
        level=20,
    )
    backfill.backfill_approved_via_event(apps, None)
    sample_join_request.refresh_from_db()
    assert sample_join_request.approved_via_event is None
