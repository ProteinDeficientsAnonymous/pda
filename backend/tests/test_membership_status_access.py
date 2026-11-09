import pytest
from community.events.limited_access import is_limited
from django.utils import timezone
from users.models import MembershipStatus, User, can_sign_in_q, limited_q

from tests._users import make_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("status", "signs_in", "limited"),
    [
        (MembershipStatus.MEMBER, True, False),
        (MembershipStatus.TENTATIVE, True, True),
        (MembershipStatus.ATTENDANCE_PAUSED, True, True),
        (MembershipStatus.PUBLIC_RSVPER, False, False),
        (MembershipStatus.REJECTED, False, False),
        (MembershipStatus.ARCHIVED, False, False),
    ],
)
def test_access_queries_follow_status(status, signs_in, limited):
    user = make_user(membership_status=status, is_member=status == MembershipStatus.MEMBER)
    assert User.objects.filter(can_sign_in_q(), pk=user.pk).exists() is signs_in
    assert User.objects.filter(limited_q(), pk=user.pk).exists() is limited


def test_archived_member_cannot_sign_in():
    user = make_user(is_member=True, archived_at=timezone.now())
    assert not User.objects.filter(can_sign_in_q(), pk=user.pk).exists()


def test_guidelines_paused_tentative_is_not_limited():
    user = make_user(membership_status=MembershipStatus.TENTATIVE, is_member=False, is_paused=True)
    assert not User.objects.filter(limited_q(), pk=user.pk).exists()


def test_rejected_user_who_signs_in_stays_limited():
    assert is_limited(make_user(membership_status=MembershipStatus.REJECTED, is_member=False))


def test_members_excludes_archived_member():
    archived = make_user(is_member=True, archived_at=timezone.now())
    assert not User.objects.members().filter(pk=archived.pk).exists()


@pytest.mark.parametrize(("was_member", "included"), [(True, True), (False, False)])
def test_members_or_archived_keeps_only_archived_members(was_member, included):
    user = make_user(is_member=was_member, archived_at=timezone.now())
    assert User.objects.members_or_archived().filter(pk=user.pk).exists() is included
