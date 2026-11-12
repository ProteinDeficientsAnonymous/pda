from io import StringIO

import pytest
from community.management.commands._seed_staging_data import PASSWORD
from community.management.commands._seed_staging_statuses import STATUS_PHONE_PREFIX, status_phone
from community.models import JoinRequest, JoinRequestStatus
from community.shared import validate_display_name
from django.core.management import call_command
from users.helpers import is_admin
from users.models import MembershipStatus, User


@pytest.mark.django_db
def test_reset_seeds_admin_and_every_membership_status():
    call_command("seed_staging")
    out = StringIO()
    call_command("seed_staging", "--reset", stdout=out)

    users = list(User.objects.filter(phone_number__startswith=STATUS_PHONE_PREFIX))
    expected = set(MembershipStatus.values) - {MembershipStatus.NONE}
    assert {u.membership_status for u in users} == expected
    archived_from = {u.status_before_archive for u in users if u.archived_at is not None}
    assert archived_from == {MembershipStatus.ACTIVE_MEMBER, MembershipStatus.ATTENDANCE_PAUSED}
    for user in users:
        assert user.check_password(PASSWORD) and user.phone_number in out.getvalue()
        validate_display_name(user.first_name)
    assert is_admin(User.objects.get(phone_number=status_phone(0)))
    paused = User.objects.get(phone_number=status_phone(2))
    assert paused.attendance_paused_at is not None
    assert list(paused.roles.values_list("name", flat=True)) == ["member"]


@pytest.mark.django_db
def test_tentative_person_keeps_open_tentative_join_request_on_rerun():
    call_command("seed_staging")
    call_command("seed_staging")
    tentative = User.objects.get(phone_number=status_phone(1))
    request = JoinRequest.objects.get(phone_number=status_phone(1))
    assert tentative.membership_status == MembershipStatus.TENTATIVE
    assert request.status == JoinRequestStatus.TENTATIVE and request.user == tentative
    assert not tentative.needs_onboarding and not tentative.roles.exists()
