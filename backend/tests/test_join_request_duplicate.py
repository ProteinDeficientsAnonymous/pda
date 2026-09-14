"""A second submission from a number that already has a live request is rejected.

PENDING and TENTATIVE both count as live. REJECTED does not — a rejected
applicant may re-apply, and the new request carries `previously_rejected` so
vettors see the history.
"""

import pytest
from community._validation import Code
from community.models import JoinRequest, JoinRequestStatus
from users.models import User

from tests._asserts import assert_error_code

PHONE = "+12025551401"


def _submit(api_client, why_join_id, phone=PHONE, email="sprout@example.com"):
    return api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Sprout",
            "last_name": "Seedling",
            "phone_number": phone,
            "email": email,
            "answers": {why_join_id: "Liberation."},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )


@pytest.mark.django_db
class TestDuplicateSubmission:
    def test_pending_request_blocks_resubmission(self, api_client, why_join_id):
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=PHONE, status=JoinRequestStatus.PENDING
        )
        response = _submit(api_client, why_join_id)
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.PHONE_ALREADY_PENDING)
        assert JoinRequest.objects.filter(phone_number=PHONE).count() == 1

    def test_tentative_request_blocks_resubmission(self, api_client, why_join_id):
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=PHONE, status=JoinRequestStatus.TENTATIVE
        )
        response = _submit(api_client, why_join_id)
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.PHONE_ALREADY_TENTATIVE)
        assert JoinRequest.objects.filter(phone_number=PHONE).count() == 1

    def test_tentative_request_blocks_even_with_linked_non_member(self, api_client, why_join_id):
        user = User.objects.create(phone_number=PHONE, first_name="Sprout", is_member=False)
        JoinRequest.objects.create(
            first_name="Sprout",
            phone_number=PHONE,
            user=user,
            status=JoinRequestStatus.TENTATIVE,
        )
        response = _submit(api_client, why_join_id)
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.PHONE_ALREADY_TENTATIVE)

    def test_rejected_request_allows_resubmission(self, api_client, why_join_id):
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=PHONE, status=JoinRequestStatus.REJECTED
        )
        response = _submit(api_client, why_join_id)
        assert response.status_code == 201
        assert JoinRequest.objects.filter(phone_number=PHONE).count() == 2

    def test_resubmission_after_rejection_is_flagged(self, api_client, why_join_id, vettor_headers):
        JoinRequest.objects.create(
            first_name="Sprout", phone_number=PHONE, status=JoinRequestStatus.REJECTED
        )
        _submit(api_client, why_join_id)
        listing = api_client.get("/api/community/join-requests/", **vettor_headers).json()
        fresh = next(r for r in listing if r["status"] == JoinRequestStatus.PENDING)
        assert fresh["previously_rejected"] is True

    def test_first_time_applicant_is_not_flagged(self, api_client, why_join_id, vettor_headers):
        _submit(api_client, why_join_id)
        listing = api_client.get("/api/community/join-requests/", **vettor_headers).json()
        fresh = next(r for r in listing if r["phone_number"] == PHONE)
        assert fresh["previously_rejected"] is False
