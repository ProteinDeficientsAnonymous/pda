"""A second submission from a number that already has a live request is rejected.

PENDING and TENTATIVE both count as live. REJECTED does not — a rejected
applicant may re-apply, and the new request carries `previously_rejected` so
vettors see the history.
"""

from unittest.mock import patch

import pytest
from community.join_requests import submit
from community.models import JoinRequest, JoinRequestStatus, RejectionReason
from community.validation import Code
from django.db import IntegrityError, transaction
from django.utils import timezone
from users.models import MembershipStatus, User

from tests._asserts import assert_error_code
from tests._users import make_attendance_paused

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
        user = User.objects.create(
            phone_number=PHONE,
            first_name="Sprout",
            membership_status=MembershipStatus.NONE,
        )
        JoinRequest.objects.create(
            first_name="Sprout",
            phone_number=PHONE,
            user=user,
            status=JoinRequestStatus.TENTATIVE,
        )
        response = _submit(api_client, why_join_id)
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.PHONE_ALREADY_TENTATIVE)

    def test_attendance_paused_member_is_already_a_member(self, api_client, why_join_id):
        make_attendance_paused(phone_number=PHONE)
        response = _submit(api_client, why_join_id)
        assert response.status_code == 409
        assert_error_code(response, Code.JoinRequest.ALREADY_MEMBER)
        assert not JoinRequest.objects.filter(phone_number=PHONE).exists()

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

    def test_resubmission_shows_the_latest_earlier_rejection(
        self, api_client, why_join_id, vettor_headers, vettor_user
    ):
        for note in ("first try", "second try"):
            JoinRequest.objects.create(
                phone_number=PHONE,
                status=JoinRequestStatus.REJECTED,
                status_changed_at=timezone.now(),
                status_changed_by=vettor_user,
                rejection_reason=RejectionReason.OTHER,
                rejection_note=note,
            )
        _submit(api_client, why_join_id)
        listing = api_client.get("/api/community/join-requests/", **vettor_headers).json()
        by_status = {r["status"]: r for r in listing if r["rejection_note"] != "first try"}
        assert by_status[JoinRequestStatus.PENDING]["previous_rejection"] == {
            "status_changed_at": by_status[JoinRequestStatus.REJECTED]["status_changed_at"],
            "status_changed_by_name": "Vettor",
            "rejection_reason": RejectionReason.OTHER,
            "rejection_note": "second try",
        }
        assert by_status[JoinRequestStatus.REJECTED]["previous_rejection"]["rejection_note"] == (
            "first try"
        )

    def test_first_time_applicant_is_not_flagged(self, api_client, why_join_id, vettor_headers):
        _submit(api_client, why_join_id)
        listing = api_client.get("/api/community/join-requests/", **vettor_headers).json()
        fresh = next(r for r in listing if r["phone_number"] == PHONE)
        assert fresh["previously_rejected"] is False


@pytest.mark.django_db
class TestOpenRequestConstraint:
    @pytest.mark.parametrize(
        "existing,new",
        [
            (JoinRequestStatus.PENDING, JoinRequestStatus.PENDING),
            (JoinRequestStatus.PENDING, JoinRequestStatus.TENTATIVE),
            (JoinRequestStatus.TENTATIVE, JoinRequestStatus.TENTATIVE),
        ],
    )
    def test_second_open_request_for_phone_is_rejected(self, existing, new):
        JoinRequest.objects.create(phone_number=PHONE, status=existing)
        with pytest.raises(IntegrityError), transaction.atomic():
            JoinRequest.objects.create(phone_number=PHONE, status=new)

    def test_closed_requests_do_not_count(self):
        JoinRequest.objects.create(phone_number=PHONE, status=JoinRequestStatus.REJECTED)
        JoinRequest.objects.create(phone_number=PHONE, status=JoinRequestStatus.APPROVED)
        JoinRequest.objects.create(phone_number=PHONE, status=JoinRequestStatus.PENDING)
        assert JoinRequest.objects.filter(phone_number=PHONE).count() == 3

    @pytest.mark.parametrize(
        "existing,code",
        [
            (JoinRequestStatus.PENDING, Code.JoinRequest.PHONE_ALREADY_PENDING),
            (JoinRequestStatus.TENTATIVE, Code.JoinRequest.PHONE_ALREADY_TENTATIVE),
        ],
    )
    def test_racing_submission_gets_the_open_request_error(
        self, api_client, why_join_id, existing, code
    ):
        JoinRequest.objects.create(phone_number=PHONE, status=existing)
        real_check = submit._raise_if_open_request
        # The pre-check misses the row, as when a concurrent submit commits right after it.
        with patch.object(submit, "_raise_if_open_request") as check:
            check.side_effect = lambda phone: None if check.call_count == 1 else real_check(phone)
            response = _submit(api_client, why_join_id)
        assert response.status_code == 400
        assert_error_code(response, code)
        assert JoinRequest.objects.filter(phone_number=PHONE).count() == 1
