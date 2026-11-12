from io import StringIO

import pytest
from community.management.commands._seed_staging_data import PASSWORD
from community.management.commands._seed_staging_statuses import (
    STATUS_PHONE_PREFIX,
    STATUS_SPECS,
    status_phone,
)
from community.models import JoinRequest, JoinRequestStatus
from community.shared import validate_display_name
from django.core.management import call_command
from users.helpers import is_admin
from users.models import MembershipStatus, User


def _status_users() -> dict[str, User]:
    return {
        u.phone_number: u for u in User.objects.filter(phone_number__startswith=STATUS_PHONE_PREFIX)
    }


@pytest.mark.django_db
def test_reset_seeds_every_membership_status():
    call_command("seed_staging")
    out = StringIO()
    call_command("seed_staging", "--reset", stdout=out)

    users = _status_users()
    assert len(users) == len(STATUS_SPECS) + 1
    statuses = {u.membership_status for u in users.values()}
    assert set(MembershipStatus.values) - statuses == {MembershipStatus.NONE}
    archived = {
        u.status_before_archive
        for u in users.values()
        if u.membership_status == MembershipStatus.ARCHIVED
    }
    assert archived == {MembershipStatus.ACTIVE_MEMBER, MembershipStatus.ATTENDANCE_PAUSED}
    assert all(u.check_password(PASSWORD) for u in users.values())
    for user in users.values():
        validate_display_name(user.first_name)
        assert user.phone_number in out.getvalue()


@pytest.mark.django_db
def test_admin_holds_admin_role_and_paused_people_keep_member_role():
    call_command("seed_staging")
    users = _status_users()
    assert is_admin(users[status_phone(0)])
    paused = User.objects.get(phone_number=status_phone(2))
    assert paused.is_attendance_paused and paused.attendance_paused_at is not None
    assert set(paused.roles.values_list("name", flat=True)) == {"member"}


@pytest.mark.django_db
def test_tentative_person_has_open_tentative_join_request():
    call_command("seed_staging")
    call_command("seed_staging")
    tentative = User.objects.get(phone_number=status_phone(1))
    request = JoinRequest.objects.get(phone_number=status_phone(1))
    assert tentative.membership_status == MembershipStatus.TENTATIVE
    assert request.status == JoinRequestStatus.TENTATIVE and request.user == tentative
    assert not tentative.needs_onboarding and not tentative.roles.exists()
