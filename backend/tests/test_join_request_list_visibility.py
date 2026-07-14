"""Tests for onboarding-driven visibility of approved join requests in the list."""

from datetime import timedelta

import pytest
from community.models import JoinRequestStatus
from django.utils import timezone
from users.models import User


@pytest.mark.django_db
class TestJoinRequestListVisibility:
    def test_list_excludes_reapproved_onboarded_user_past_grace(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        # onboarded_at is set once and never cleared; a re-approval flips
        # needs_onboarding back to True, leaving the contradictory state that
        # used to keep the request in the approved list forever.
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.onboarded_at = timezone.now() - timedelta(days=60)
        user.needs_onboarding = True
        user.save(update_fields=["onboarded_at", "needs_onboarding"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) not in ids

    def test_list_includes_onboarded_user_within_grace(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.onboarded_at = timezone.now() - timedelta(days=1)
        user.needs_onboarding = False
        user.save(update_fields=["onboarded_at", "needs_onboarding"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) in ids
