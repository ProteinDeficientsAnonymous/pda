import importlib

import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.apps import apps
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._users import make_user

pytestmark = pytest.mark.django_db

backfill = importlib.import_module("users.migrations.0059_backfill_membership_status")


def _status_after_backfill(user):
    backfill.backfill_membership_status(apps, None)
    user.refresh_from_db()
    return user.membership_status


def _link_request(user, sample_join_request, status, **fields):
    sample_join_request.user = user
    sample_join_request.status = status
    for name, value in fields.items():
        setattr(sample_join_request, name, value)
    sample_join_request.save()


def test_member():
    assert (
        _status_after_backfill(make_user(membership_status=MembershipStatus.MEMBER))
        == MembershipStatus.MEMBER
    )


def test_plain_non_member_is_public_rsvper():
    assert (
        _status_after_backfill(make_user(membership_status=MembershipStatus.PUBLIC_RSVPER))
        == MembershipStatus.PUBLIC_RSVPER
    )


def test_tentative(sample_join_request):
    user = make_user(membership_status=MembershipStatus.PUBLIC_RSVPER)
    _link_request(user, sample_join_request, JoinRequestStatus.TENTATIVE)
    assert _status_after_backfill(user) == MembershipStatus.TENTATIVE


def test_rejected_after_tentative(sample_join_request):
    user = make_user(membership_status=MembershipStatus.PUBLIC_RSVPER)
    _link_request(
        user, sample_join_request, JoinRequestStatus.REJECTED, tentative_at=timezone.now()
    )
    assert _status_after_backfill(user) == MembershipStatus.REJECTED


def test_tentative_wins_over_older_rejection(sample_join_request):
    user = make_user(membership_status=MembershipStatus.PUBLIC_RSVPER)
    JoinRequest.objects.create(
        user=user,
        phone_number="+16505550199",
        status=JoinRequestStatus.REJECTED,
        tentative_at=timezone.now(),
    )
    _link_request(user, sample_join_request, JoinRequestStatus.TENTATIVE)
    assert _status_after_backfill(user) == MembershipStatus.TENTATIVE


def test_public_rsvper_rejected_without_tentative_stays_public_rsvper(sample_join_request):
    user = make_user(membership_status=MembershipStatus.PUBLIC_RSVPER)
    _link_request(user, sample_join_request, JoinRequestStatus.REJECTED)
    assert _status_after_backfill(user) == MembershipStatus.PUBLIC_RSVPER


def test_attendance_paused():
    user = make_user(
        membership_status=MembershipStatus.ATTENDANCE_PAUSED, attendance_paused_at=timezone.now()
    )
    assert _status_after_backfill(user) == MembershipStatus.ATTENDANCE_PAUSED


def test_archived_member_is_archived():
    user = make_user(membership_status=MembershipStatus.ARCHIVED, archived_at=timezone.now())
    assert _status_after_backfill(user) == MembershipStatus.ARCHIVED


def test_archived_wins_over_attendance_pause():
    user = make_user(
        membership_status=MembershipStatus.ARCHIVED,
        attendance_paused_at=timezone.now(),
        archived_at=timezone.now(),
    )
    assert _status_after_backfill(user) == MembershipStatus.ARCHIVED


def test_member_wins_over_old_rejected_request(sample_join_request):
    user = make_user(membership_status=MembershipStatus.MEMBER)
    _link_request(
        user, sample_join_request, JoinRequestStatus.REJECTED, tentative_at=timezone.now()
    )
    assert _status_after_backfill(user) == MembershipStatus.MEMBER


guidelines_backfill = importlib.import_module("users.migrations.0062_guidelines_paused_status")


@pytest.mark.parametrize(
    ("is_paused", "before", "expected"),
    [
        (True, MembershipStatus.MEMBER, MembershipStatus.GUIDELINES_PAUSED),
        (True, MembershipStatus.ATTENDANCE_PAUSED, MembershipStatus.GUIDELINES_PAUSED),
        (True, MembershipStatus.ARCHIVED, MembershipStatus.ARCHIVED),
        (False, MembershipStatus.MEMBER, MembershipStatus.MEMBER),
        (False, MembershipStatus.ATTENDANCE_PAUSED, MembershipStatus.ATTENDANCE_PAUSED),
    ],
)
def test_guidelines_paused_backfill(is_paused, before, expected):
    user = make_user(is_paused=is_paused, attendance_paused_at=timezone.now())
    User.objects.filter(pk=user.pk).update(membership_status=before)
    guidelines_backfill.backfill_guidelines_paused(apps, None)
    user.refresh_from_db()
    assert user.membership_status == expected
    assert (user.attendance_paused_at is None) == (expected == MembershipStatus.GUIDELINES_PAUSED)
