import pytest
from community.join_requests.approval import maybe_promote_tentative
from community.models import JoinRequestStatus
from users.models import MEMBER_STATUSES, MembershipStatus

from tests._public_rsvp_helpers import make_public_rsvper
from tests._tentative_helpers import open_official_event, tentative_user_with_rsvp

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


def test_check_in_promotes_tentative_to_member(
    sample_join_request, vettor_user, open_official_event
):
    user = tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
    assert maybe_promote_tentative(user, open_official_event, vettor_user)
    assert _assert_in_sync(user) == MembershipStatus.ACTIVE_MEMBER
    assert user.membership_status_changed_by == vettor_user
