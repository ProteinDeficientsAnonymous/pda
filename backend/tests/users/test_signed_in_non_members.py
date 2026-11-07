import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from tests._users import make_user
from users.models import User


def _attendance_paused(**fields) -> User:
    return make_user(is_member=False, attendance_paused_at=timezone.now(), **fields)


def _tentative() -> User:
    user = make_user(is_member=False)
    for _ in range(2):
        JoinRequest.objects.create(
            first_name="Sprout",
            phone_number=user.phone_number,
            user=user,
            status=JoinRequestStatus.TENTATIVE,
        )
    return user


@pytest.mark.django_db
class TestSignedInNonMembers:
    def test_is_tentative_applicants_and_attendance_paused_members(self):
        paused = _attendance_paused()
        tentative = _tentative()
        make_user(is_member=True)
        make_user(is_member=False)
        assert sorted(User.objects.signed_in_non_members(), key=str) == sorted(
            [paused, tentative], key=str
        )

    def test_active_tentative_members_includes_attendance_paused_but_not_guidelines_paused(self):
        paused = _attendance_paused()
        _attendance_paused(is_paused=True)
        assert list(User.objects.active_tentative_members()) == [paused]
