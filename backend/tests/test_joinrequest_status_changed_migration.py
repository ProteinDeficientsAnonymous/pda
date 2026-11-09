import importlib
from datetime import timedelta

import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.apps import apps
from django.utils import timezone

pytestmark = pytest.mark.django_db

migration = importlib.import_module("community.migrations.0133_joinrequest_status_changed")


def _fill_and_read(jr: JoinRequest) -> tuple:
    migration.fill_status_changed(apps, None)
    jr.refresh_from_db()
    return jr.status_changed_at, jr.status_changed_by


def test_rejected_takes_the_rejection_stamp(vettor_user, test_user):
    now = timezone.now()
    jr = JoinRequest.objects.create(
        phone_number="+16505550001",
        status=JoinRequestStatus.REJECTED,
        tentative_at=now - timedelta(days=2),
        tentative_by=test_user,
        rejected_at=now,
        rejected_by=vettor_user,
    )
    assert _fill_and_read(jr) == (now, vettor_user)


def test_approved_after_tentative_takes_the_approval_stamp(vettor_user, test_user):
    now = timezone.now()
    jr = JoinRequest.objects.create(
        phone_number="+16505550002",
        status=JoinRequestStatus.APPROVED,
        tentative_at=now - timedelta(days=2),
        tentative_by=vettor_user,
        approved_at=now,
        approved_by=test_user,
    )
    assert _fill_and_read(jr) == (now, test_user)


def test_tentative_after_unreject_takes_the_tentative_stamp(vettor_user, test_user):
    now = timezone.now()
    jr = JoinRequest.objects.create(
        phone_number="+16505550003",
        status=JoinRequestStatus.TENTATIVE,
        rejected_at=now - timedelta(days=2),
        rejected_by=vettor_user,
        tentative_at=now,
        tentative_by=test_user,
    )
    assert _fill_and_read(jr) == (now, test_user)


def test_approved_without_approval_stamp_stays_empty(vettor_user):
    jr = JoinRequest.objects.create(
        phone_number="+16505550004",
        status=JoinRequestStatus.APPROVED,
        tentative_at=timezone.now(),
        tentative_by=vettor_user,
    )
    assert _fill_and_read(jr) == (None, None)


def test_unrejected_pending_stays_empty(vettor_user):
    jr = JoinRequest.objects.create(
        phone_number="+16505550005", rejected_at=timezone.now(), rejected_by=vettor_user
    )
    assert _fill_and_read(jr) == (None, None)
