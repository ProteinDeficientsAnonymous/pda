"""Tests for the un-reject join request flow."""

import pytest
from community.models import JoinRequestStatus


@pytest.mark.django_db
class TestUnrejectJoinRequest:
    def test_unreject_success(self, api_client, vettor_headers, vettor_user, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == JoinRequestStatus.PENDING
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == JoinRequestStatus.PENDING
        assert sample_join_request.rejected_by == vettor_user
        assert sample_join_request.rejected_at is not None

    def test_unreject_pending_fails(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400

    def test_unreject_approved_fails(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400

    def test_unreject_requires_permission(self, api_client, auth_headers, sample_join_request):
        sample_join_request.status = JoinRequestStatus.REJECTED
        sample_join_request.save(update_fields=["status"])
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_unreject_unauthenticated(self, api_client, sample_join_request):
        sample_join_request.status = JoinRequestStatus.REJECTED
        sample_join_request.save(update_fields=["status"])
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_unreject_not_found(self, api_client, vettor_headers):
        import uuid

        response = api_client.patch(
            f"/api/community/join-requests/{uuid.uuid4()}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 404

    def test_unreject_then_reject_again_works(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/unreject/",
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == JoinRequestStatus.REJECTED
