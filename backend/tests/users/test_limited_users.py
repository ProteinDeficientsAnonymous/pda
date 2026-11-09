import pytest
from django.utils import timezone
from tests._digest_helpers import make_tentative
from tests._users import make_attendance_paused, make_user
from users.models import MembershipStatus, User


@pytest.mark.django_db
class TestLimitedUsers:
    def test_is_tentative_applicants_and_attendance_paused_members(self):
        paused = make_attendance_paused()
        tentative = make_tentative("+12025550290")
        make_user(membership_status=MembershipStatus.ACTIVE_MEMBER)
        make_user(membership_status=MembershipStatus.NONE)
        pks = list(User.objects.limited_users().values_list("pk", flat=True))
        assert sorted(pks) == sorted([paused.pk, tentative.pk])

    def test_excludes_guidelines_paused(self):
        make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED)
        assert not User.objects.limited_users().exists()

    def test_active_limited_users_excludes_archived(self):
        paused = make_attendance_paused()
        make_attendance_paused(archived_at=timezone.now())
        assert list(User.objects.active_limited_users()) == [paused]
