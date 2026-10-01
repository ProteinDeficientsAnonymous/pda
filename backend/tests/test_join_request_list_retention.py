from datetime import timedelta

import pytest
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from users.models import User


@pytest.mark.django_db
class TestJoinRequestListRetention:
    def test_list_excludes_approved_onboarded_user_after_grace(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.onboarded_at = timezone.now() - timedelta(days=8)
        user.has_joined_whatsapp = True
        user.save(update_fields=["needs_onboarding", "onboarded_at", "has_joined_whatsapp"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) not in ids

    def test_list_includes_approved_onboarded_within_grace(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.onboarded_at = timezone.now() - timedelta(days=6)
        user.save(update_fields=["needs_onboarding", "onboarded_at"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        items = {r["id"]: r for r in response.json()}
        assert str(sample_join_request.id) in items
        assert items[str(sample_join_request.id)]["onboarded_at"] is not None

    def test_list_excludes_legacy_onboarded_user_with_null_timestamp(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.onboarded_at = None
        user.has_joined_whatsapp = True
        user.save(update_fields=["needs_onboarding", "onboarded_at", "has_joined_whatsapp"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) not in ids

    @pytest.mark.parametrize(
        "case",
        [
            (JoinRequestStatus.APPROVED, False, True),
            (JoinRequestStatus.TENTATIVE, False, True),
            (JoinRequestStatus.TENTATIVE, True, False),
        ],
    )
    def test_list_keeps_members_until_whatsapp_joined_after_grace(
        self, api_client, vettor_headers, sample_join_request, case
    ):
        status, joined_whatsapp, visible = case
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": status},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.onboarded_at = timezone.now() - timedelta(days=30)
        user.has_joined_whatsapp = joined_whatsapp
        user.save(update_fields=["needs_onboarding", "onboarded_at", "has_joined_whatsapp"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        ids = [r["id"] for r in response.json()]
        assert (str(sample_join_request.id) in ids) is visible

    def test_list_includes_whatsapp_joined_within_grace(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.onboarded_at = timezone.now() - timedelta(days=2)
        user.has_joined_whatsapp = True
        user.save(update_fields=["needs_onboarding", "onboarded_at", "has_joined_whatsapp"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) in ids

    def test_list_includes_approved_not_yet_onboarded(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        items = {r["id"]: r for r in response.json()}
        assert str(sample_join_request.id) in items
        assert items[str(sample_join_request.id)]["onboarded_at"] is None

    def test_list_keeps_pending_and_rejected_unaffected(self, api_client, vettor_headers, db):
        pending = JoinRequest.objects.create(
            first_name="Pending",
            last_name="Person",
            phone_number="+12025550101",
            status=JoinRequestStatus.PENDING,
        )
        rejected = JoinRequest.objects.create(
            first_name="Rejected",
            last_name="Person",
            phone_number="+12025550102",
            status=JoinRequestStatus.REJECTED,
        )
        approved = JoinRequest.objects.create(
            first_name="Onboarded",
            last_name="Person",
            phone_number="+12025550103",
            status=JoinRequestStatus.APPROVED,
        )
        User.objects.create_user(
            phone_number="+12025550103",
            first_name="Onboarded",
            last_name="Person",
            needs_onboarding=False,
            has_joined_whatsapp=True,
        )

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(pending.id) in ids
        assert str(rejected.id) in ids
        assert str(approved.id) not in ids
