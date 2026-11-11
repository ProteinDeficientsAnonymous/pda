import pytest
from community.join_requests.approval import maybe_promote_tentative
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import MembershipStatus, Role

from tests._tentative_helpers import open_official_event
from tests._users import make_user

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db

PHONE = "+16505551234"


@pytest.fixture
def archived_member(vettor_user):
    member = make_user(
        phone_number=PHONE, archived_at=timezone.now(), membership_status_changed_by=vettor_user
    )
    member.roles.add(*Role.objects.filter(name="member", is_default=True))
    assert member.roles.exists()
    return member


def _decide(api_client, headers, join_request, status):
    response = api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    return response.json()


def test_marking_tentative_unarchives(
    api_client, vettor_headers, sample_join_request, archived_member
):
    body = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    archived_member.refresh_from_db()
    assert archived_member.membership_status == MembershipStatus.TENTATIVE
    assert archived_member.archived_at is None
    assert not archived_member.roles.exists()

    login = api_client.get(f"/api/auth/magic-login/{body['magic_link_token']}/")
    assert login.status_code == 200


def test_tentative_then_approved_is_a_member(
    api_client, vettor_headers, sample_join_request, archived_member
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    archived_member.refresh_from_db()
    assert archived_member.membership_status == MembershipStatus.ACTIVE_MEMBER
    assert archived_member.roles.filter(name="member").exists()


@pytest.mark.parametrize(
    ("pause", "status"),
    [
        ({}, MembershipStatus.GUIDELINES_PAUSED),
        ({"attendance_paused_at": timezone.now()}, MembershipStatus.ATTENDANCE_PAUSED),
    ],
)
def test_marking_tentative_keeps_an_archived_pause(
    api_client, vettor_headers, sample_join_request, pause, status
):
    paused = make_user(
        phone_number=PHONE, archived_at=timezone.now(), status_before_archive=status, **pause
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    paused.refresh_from_db()
    assert paused.membership_status == status
    assert paused.archived_at is None
    assert paused.status_before_archive is None


def test_check_in_does_not_promote_a_guidelines_paused_tentative(
    api_client, vettor_headers, sample_join_request, vettor_user, open_official_event
):
    paused = make_user(
        phone_number=PHONE,
        archived_at=timezone.now(),
        status_before_archive=MembershipStatus.GUIDELINES_PAUSED,
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    paused.refresh_from_db()
    assert not maybe_promote_tentative(paused, open_official_event, vettor_user)
    assert paused.membership_status == MembershipStatus.GUIDELINES_PAUSED
