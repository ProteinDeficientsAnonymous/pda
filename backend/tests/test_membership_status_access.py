import pytest
from django.utils import timezone
from users.models import MembershipStatus, User, can_sign_in_q, limited_q

from tests._users import make_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("status", "signs_in", "limited"),
    [
        (MembershipStatus.ACTIVE_MEMBER, True, False),
        (MembershipStatus.TENTATIVE, True, True),
        (MembershipStatus.ATTENDANCE_PAUSED, True, True),
        (MembershipStatus.NONE, False, False),
        (MembershipStatus.ARCHIVED, False, False),
    ],
)
def test_access_queries_follow_status(status, signs_in, limited):
    user = make_user(membership_status=status)
    assert User.objects.filter(can_sign_in_q(), pk=user.pk).exists() is signs_in
    assert User.objects.filter(limited_q(), pk=user.pk).exists() is limited


def test_archived_member_cannot_sign_in():
    user = make_user(membership_status=MembershipStatus.ARCHIVED, archived_at=timezone.now())
    assert not User.objects.filter(can_sign_in_q(), pk=user.pk).exists()


def test_guidelines_paused_is_not_limited():
    user = make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED)
    assert not User.objects.filter(limited_q(), pk=user.pk).exists()
