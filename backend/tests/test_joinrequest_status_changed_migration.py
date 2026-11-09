import importlib
from datetime import timedelta

import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.apps import apps
from django.utils import timezone

pytestmark = pytest.mark.django_db

migration = importlib.import_module("community.migrations.0133_joinrequest_status_changed")


def test_fill_takes_the_newest_stamp(vettor_user, test_user):
    now = timezone.now()
    rejected = JoinRequest.objects.create(
        phone_number="+16505550001",
        status=JoinRequestStatus.REJECTED,
        tentative_at=now - timedelta(days=2),
        tentative_by=test_user,
        rejected_at=now,
        rejected_by=vettor_user,
    )
    unrejected = JoinRequest.objects.create(
        phone_number="+16505550002", rejected_at=now, rejected_by=vettor_user
    )
    migration.fill_status_changed(apps, None)
    rejected.refresh_from_db()
    unrejected.refresh_from_db()
    assert (rejected.status_changed_at, rejected.status_changed_by) == (now, vettor_user)
    assert unrejected.status_changed_at is None
