import pytest
from audit.models import AuditLogEntry
from community.join_requests.approval import maybe_promote_tentative
from community.models import JoinRequest, JoinRequestStatus
from community.validation import Code
from users.models import MembershipStatus

from tests._asserts import assert_error_code
from tests._tentative_helpers import decide, open_official_event, tentative_user_with_rsvp

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db

PHONE = "+16505551234"


@pytest.fixture
def tentative(sample_join_request, open_official_event, vettor_user):
    return tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)


def _archive(api_client, headers, user):
    return api_client.delete(f"/api/auth/users/{user.id}/", **headers)


@pytest.fixture
def archived(api_client, manage_users_headers, tentative, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        assert _archive(api_client, manage_users_headers, tentative).status_code == 204
    tentative.refresh_from_db()
    return tentative


def test_members_list_includes_tentative(api_client, manage_users_headers, tentative):
    response = api_client.get("/api/auth/users/", **manage_users_headers)

    assert response.status_code == 200
    row = next(u for u in response.json() if u["id"] == str(tentative.id))
    assert row["membership_status"] == MembershipStatus.TENTATIVE


def test_archiving_tentative_closes_request(manage_users_user, archived, sample_join_request):
    sample_join_request.refresh_from_db()
    assert sample_join_request.status == JoinRequestStatus.CLOSED
    assert sample_join_request.status_changed_by == manage_users_user
    assert sample_join_request.status_changed_at is not None
    assert archived.membership_status == MembershipStatus.ARCHIVED
    assert archived.status_before_archive == MembershipStatus.TENTATIVE
    assert AuditLogEntry.objects.filter(
        action="join_request_closed", target_id=str(sample_join_request.id)
    ).exists()


def test_non_admin_cannot_archive(api_client, vettor_headers, tentative, sample_join_request):
    assert _archive(api_client, vettor_headers, tentative).status_code == 403

    sample_join_request.refresh_from_db()
    assert sample_join_request.status == JoinRequestStatus.TENTATIVE


def test_check_in_does_not_promote_archived_tentative(
    manage_users_user, archived, open_official_event
):
    assert not maybe_promote_tentative(archived, open_official_event, manage_users_user)
    archived.refresh_from_db()
    assert archived.membership_status == MembershipStatus.ARCHIVED
    assert not JoinRequest.objects.filter(status=JoinRequestStatus.APPROVED).exists()


@pytest.mark.parametrize(
    "status",
    [JoinRequestStatus.TENTATIVE, JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED],
)
def test_closed_request_is_terminal(
    api_client, vettor_headers, archived, sample_join_request, status
):
    response = decide(api_client, vettor_headers, sample_join_request, status)

    assert response.status_code == 400
    assert_error_code(response, Code.JoinRequest.ALREADY_DECIDED)
    sample_join_request.refresh_from_db()
    assert sample_join_request.status == JoinRequestStatus.CLOSED


def test_archived_tentative_can_reapply_with_history(
    api_client, manage_users_user, vettor_headers, why_join_id, archived
):
    submitted = api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Sprout",
            "last_name": "Again",
            "phone_number": PHONE,
            "email": "sprout@example.com",
            "answers": {why_join_id: "trying again"},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )
    assert submitted.status_code == 201
    new_id = submitted.json()["id"]

    rows = api_client.get("/api/community/join-requests/", **vettor_headers).json()
    row = next(r for r in rows if r["id"] == new_id)
    assert row["previously_archived"] is True
    assert row["previous_archive"]["archived_by_name"] == manage_users_user.full_name

    new_request = JoinRequest.objects.get(id=new_id)
    assert (
        decide(api_client, vettor_headers, new_request, JoinRequestStatus.TENTATIVE).status_code
        == 200
    )
    archived.refresh_from_db()
    assert archived.membership_status == MembershipStatus.TENTATIVE
    assert archived.archived_at is None
    assert archived.status_before_archive is None
