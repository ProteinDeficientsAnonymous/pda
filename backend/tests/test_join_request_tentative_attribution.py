import pytest
from community.models import JoinRequestStatus

pytestmark = pytest.mark.django_db


def _decide(api_client, headers, join_request, status):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )


def test_tentative_stamps_who_and_when(
    api_client, vettor_headers, vettor_user, sample_join_request
):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    sample_join_request.refresh_from_db()
    assert sample_join_request.status_changed_by == vettor_user
    assert sample_join_request.status_changed_at is not None


def test_final_approval_restamps_status_change(api_client, vettor_headers, sample_join_request):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    sample_join_request.refresh_from_db()
    tentative_at = sample_join_request.status_changed_at
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.APPROVED)
    sample_join_request.refresh_from_db()
    assert sample_join_request.status_changed_at > tentative_at


def test_list_exposes_status_change(api_client, vettor_headers, sample_join_request):
    _decide(api_client, vettor_headers, sample_join_request, JoinRequestStatus.TENTATIVE)
    response = api_client.get("/api/community/join-requests/", **vettor_headers)
    row = next(r for r in response.json() if r["id"] == str(sample_join_request.id))
    assert row["status_changed_by_name"] == "Vettor"
    assert row["status_changed_at"] is not None
