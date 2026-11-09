import pytest
from community.join_requests.approval import maybe_promote_tentative
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import MEMBER_STATUSES, MembershipStatus

from tests._public_rsvp_helpers import make_public_rsvper
from tests._tentative_helpers import open_official_event, tentative_user_with_rsvp
from tests._users import make_user

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db


def _decide(api_client, headers, join_request, status):
    response = api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )
    assert response.status_code == 200
    join_request.refresh_from_db()
    return join_request.user


def _assert_in_sync(user):
    user.refresh_from_db()
    assert user.is_member == (user.membership_status in MEMBER_STATUSES)
    return user.membership_status


def test_tentative_creates_tentative_user(api_client, vettor_headers, sample_join_request):
    user = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    assert _assert_in_sync(user) == MembershipStatus.TENTATIVE


def test_tentative_moves_linked_public_rsvper(api_client, vettor_headers, sample_join_request):
    rsvper = make_public_rsvper(sample_join_request.phone_number, "sprout@example.test")
    sample_join_request.user = rsvper
    sample_join_request.save(update_fields=["user"])
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    assert _assert_in_sync(rsvper) == MembershipStatus.TENTATIVE


def test_rejecting_public_rsvper_leaves_status(api_client, vettor_headers, sample_join_request):
    rsvper = make_public_rsvper(sample_join_request.phone_number, "sprout@example.test")
    sample_join_request.user = rsvper
    sample_join_request.save(update_fields=["user"])
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.REJECTED)
    assert _assert_in_sync(rsvper) == MembershipStatus.NONE


def test_approving_tentative_user_makes_member(api_client, vettor_headers, sample_join_request):
    user = _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    assert _assert_in_sync(user) == MembershipStatus.ACTIVE_MEMBER


def test_approving_public_rsvper_makes_member(api_client, vettor_headers, sample_join_request):
    rsvper = make_public_rsvper(sample_join_request.phone_number, "sprout@example.test")
    sample_join_request.user = rsvper
    sample_join_request.save(update_fields=["user"])
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    assert _assert_in_sync(rsvper) == MembershipStatus.ACTIVE_MEMBER


def test_reapproving_archived_member_makes_member(api_client, vettor_headers, sample_join_request):
    member = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    assert _assert_in_sync(member) == MembershipStatus.ACTIVE_MEMBER


def test_approving_linked_archived_applicant_reactivates(
    api_client, vettor_headers, sample_join_request
):
    applicant = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
    )
    sample_join_request.user = applicant
    sample_join_request.save(update_fields=["user"])
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    applicant.refresh_from_db()
    assert applicant.archived_at is None
    assert applicant.is_member is True


def test_check_in_promotes_tentative_to_member(
    sample_join_request, vettor_user, open_official_event
):
    user = tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
    assert maybe_promote_tentative(user, open_official_event, vettor_user)
    assert _assert_in_sync(user) == MembershipStatus.ACTIVE_MEMBER
    assert user.membership_status_changed_by == vettor_user


def test_reapproving_archived_applicant_makes_member(
    api_client, vettor_headers, sample_join_request
):
    applicant = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=MembershipStatus.ARCHIVED,
        archived_at=timezone.now(),
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    assert _assert_in_sync(applicant) == MembershipStatus.ACTIVE_MEMBER
    assert applicant.archived_by is None
    assert applicant.roles.filter(name="member").exists()


@pytest.mark.parametrize("is_paused", [False, True])
def test_reapproving_archived_paused_member_keeps_pause(
    api_client, vettor_headers, sample_join_request, is_paused
):
    paused = make_user(
        phone_number=sample_join_request.phone_number,
        membership_status=MembershipStatus.ARCHIVED,
        is_paused=is_paused,
        attendance_paused_at=timezone.now(),
        archived_at=timezone.now(),
    )
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    paused.refresh_from_db()
    assert paused.membership_status == (
        MembershipStatus.GUIDELINES_PAUSED if is_paused else MembershipStatus.ATTENDANCE_PAUSED
    )
    assert (paused.attendance_paused_at is None) == is_paused
