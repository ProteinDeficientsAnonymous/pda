import pytest
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._users import make_user

pytestmark = pytest.mark.django_db


def _decide(api_client, headers, join_request, status):
    response = api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200


def test_retentatived_archived_member_is_not_a_member(
    api_client, vettor_headers, sample_join_request
):
    member = make_user(
        phone_number=sample_join_request.phone_number,
        archived_at=timezone.now(),
        status_before_archive=MembershipStatus.ACTIVE_MEMBER,
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.TENTATIVE
    assert member.is_member is False
    for members in (
        User.objects.members(),
        User.objects.active_members(),
    ):
        assert not members.filter(pk=member.pk).exists()


@pytest.mark.parametrize(
    ("before", "is_member"),
    [(MembershipStatus.GUIDELINES_PAUSED, True), (MembershipStatus.ATTENDANCE_PAUSED, False)],
)
def test_retentatived_archived_pause_keeps_main_is_member(
    api_client, vettor_headers, sample_join_request, before, is_member
):
    paused = make_user(
        phone_number=sample_join_request.phone_number,
        archived_at=timezone.now(),
        status_before_archive=before,
        is_member=not is_member,
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    paused.refresh_from_db()
    assert paused.membership_status == before
    assert paused.is_member is is_member


@pytest.mark.parametrize(
    ("before", "is_member"),
    [
        (None, True),
        (MembershipStatus.ACTIVE_MEMBER, True),
        (MembershipStatus.GUIDELINES_PAUSED, True),
        (MembershipStatus.ATTENDANCE_PAUSED, False),
    ],
)
def test_reapproval_sets_main_is_member(
    api_client, vettor_headers, sample_join_request, before, is_member
):
    archived = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
        status_before_archive=before,
        is_member=not is_member,
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    archived.refresh_from_db()
    assert archived.is_member is is_member
    assert archived.archived_at is None
