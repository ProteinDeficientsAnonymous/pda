import pytest
from community.models import JoinRequest, JoinRequestStatus
from tests._digest_helpers import make_tentative
from tests._users import make_attendance_paused, make_user
from users.models import User


@pytest.mark.django_db
class TestSignedInNonMembers:
    def test_is_tentative_applicants_and_attendance_paused_members(self):
        paused = make_attendance_paused()
        tentative = make_tentative("+12025550290")
        JoinRequest.objects.create(
            first_name="Sprout",
            phone_number=tentative.phone_number,
            user=tentative,
            status=JoinRequestStatus.TENTATIVE,
        )
        make_user(is_member=True)
        make_user(is_member=False)
        pks = list(User.objects.signed_in_non_members().values_list("pk", flat=True))
        assert sorted(pks) == sorted([paused.pk, tentative.pk])

    def test_active_tentative_members_includes_attendance_paused_but_not_guidelines_paused(self):
        paused = make_attendance_paused()
        make_attendance_paused(is_paused=True)
        assert list(User.objects.active_tentative_members()) == [paused]
