"""Tests for join request management (list, approve, reject)."""

import uuid
from datetime import timedelta

import pytest
from community._validation import Code
from community.models import JoinRequest, JoinRequestStatus
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code


@pytest.mark.django_db
class TestJoinRequestManagement:
    def test_list_requires_permission(self, api_client, auth_headers):
        response = api_client.get("/api/community/join-requests/", **auth_headers)
        assert response.status_code == 403

    def test_list_unauthenticated(self, api_client):
        response = api_client.get("/api/community/join-requests/")
        assert response.status_code == 401

    def test_list_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["full_name"] == "Sprout Seedling"
        assert data[0]["status"] == JoinRequestStatus.PENDING

    def test_list_includes_email(self, api_client, vettor_headers, db):
        JoinRequest.objects.create(
            first_name="Fern",
            last_name="Frond",
            phone_number="+16505559999",
            email="fern@example.com",
        )
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        data = response.json()
        assert data[0]["email"] == "fern@example.com"

    def test_admin_can_access_list(self, api_client, db):
        admin = User.objects.create_superuser(
            phone_number="+12025550001",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
        )
        admin_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(admin).access_token}"  # type: ignore
        }
        response = api_client.get("/api/community/join-requests/", **admin_headers)
        assert response.status_code == 200

    def test_approve_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JoinRequestStatus.APPROVED
        assert data["id"] == str(sample_join_request.id)

    def test_approve_creates_user(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["magic_link_token"] is not None
        assert len(data["magic_link_token"]) == 36  # UUID format
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        assert user.full_name == "Sprout Seedling"
        assert user.needs_onboarding is True
        assert user.roles.filter(name="member").exists()

    def test_reject_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == JoinRequestStatus.REJECTED

    def test_approve_persists_status(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == JoinRequestStatus.APPROVED

    def test_invalid_status_rejected(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.PENDING},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400

    def test_requires_permission(self, api_client, auth_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_not_found(self, api_client, vettor_headers):
        response = api_client.patch(
            f"/api/community/join-requests/{uuid.uuid4()}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 404

    def test_approve_already_approved_fails(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.ALREADY_DECIDED)

    def test_approve_locks_row_for_update(
        self, api_client, vettor_headers, sample_join_request, monkeypatch
    ):
        # The already-decided guard only closes the concurrent-approval race if
        # the row is locked before the check. Assert select_for_update() is used.
        from community import _join_requests

        original = JoinRequest.objects.select_for_update
        called = False

        def spy(*args, **kwargs):
            nonlocal called
            called = True
            return original(*args, **kwargs)

        monkeypatch.setattr(_join_requests.JoinRequest.objects, "select_for_update", spy)
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert called

    def test_reject_after_reject_fails(self, api_client, vettor_headers, sample_join_request):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.JoinRequest.ALREADY_DECIDED)

    def test_approve_records_actor_and_timestamp(
        self, api_client, vettor_headers, vettor_user, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        sample_join_request.refresh_from_db()
        assert sample_join_request.approved_by == vettor_user
        assert sample_join_request.approved_at is not None
        assert sample_join_request.rejected_by is None
        assert sample_join_request.rejected_at is None

    def test_reject_records_actor_and_timestamp(
        self, api_client, vettor_headers, vettor_user, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.REJECTED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        sample_join_request.refresh_from_db()
        assert sample_join_request.rejected_by == vettor_user
        assert sample_join_request.rejected_at is not None
        assert sample_join_request.approved_by is None
        assert sample_join_request.approved_at is None

    def test_approve_creates_user_with_member_role(
        self, api_client, vettor_headers, sample_join_request, db
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["magic_link_token"] is not None
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        assert user.needs_onboarding is True

    def test_approve_duplicate_phone_skips_user_creation(
        self, api_client, vettor_headers, sample_join_request, test_user, db
    ):
        sample_join_request.phone_number = test_user.phone_number
        sample_join_request.save()
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["magic_link_token"] is None

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
        user.onboarded_at = timezone.now() - timedelta(days=4)
        user.save(update_fields=["needs_onboarding", "onboarded_at"])

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
        user.onboarded_at = timezone.now() - timedelta(days=1)
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
        user.save(update_fields=["needs_onboarding", "onboarded_at"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) not in ids

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

    def test_list_flags_previously_archived(self, api_client, vettor_headers, db):
        archived = User.objects.create_user(
            phone_number="+12025550150", first_name="Comeback", last_name="Kid"
        )
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])
        jr = JoinRequest.objects.create(
            first_name="Comeback",
            last_name="Kid",
            phone_number="+12025550150",
            status=JoinRequestStatus.PENDING,
        )

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        items = {r["id"]: r for r in response.json()}
        assert items[str(jr.id)]["previously_archived"] is True

    def test_approve_archived_user_unarchives_and_issues_magic_link(
        self, api_client, vettor_headers, db
    ):
        archived = User.objects.create_user(phone_number="+12025550151", first_name="Phoenix")
        archived.archived_at = timezone.now()
        archived.needs_onboarding = False
        archived.save(update_fields=["archived_at", "needs_onboarding"])

        jr = JoinRequest.objects.create(
            first_name="Phoenix",
            phone_number="+12025550151",
            status=JoinRequestStatus.PENDING,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["magic_link_token"] is not None
        archived.refresh_from_db()
        assert archived.archived_at is None
        assert archived.needs_onboarding is True

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
        )

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(pending.id) in ids
        assert str(rejected.id) in ids
        assert str(approved.id) not in ids


@pytest.mark.django_db
class TestApprovalEmail:
    def test_approval_copies_email_to_new_user(self, api_client, vettor_headers):
        jr = JoinRequest.objects.create(
            first_name="Applicant",
            phone_number="+12025550101",
            email="applicant@example.com",
            status=JoinRequestStatus.PENDING,
        )
        resp = api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            data={"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert resp.status_code == 200, resp.content
        user = User.objects.get(phone_number="+12025550101")
        assert user.email == "applicant@example.com"

    def test_approval_conflict_when_email_taken(self, api_client, vettor_headers):
        User.objects.create_user(
            phone_number="+12025550199", first_name="other", email="taken@example.com"
        )
        jr = JoinRequest.objects.create(
            first_name="Applicant",
            phone_number="+12025550101",
            email="taken@example.com",
            status=JoinRequestStatus.PENDING,
        )
        resp = api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            data={"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"


@pytest.mark.django_db
class TestApprovalCarriesConsent:
    def test_new_user_inherits_join_request_consent(self, api_client, vettor_headers):
        jr = JoinRequest.objects.create(
            first_name="Consenter",
            phone_number="+12025550701",
            email="consenter@example.com",
            sms_consent_at=timezone.now(),
            guidelines_consent_at=timezone.now(),
        )
        resp = api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert resp.status_code == 200, resp.content
        user = User.objects.get(phone_number="+12025550701")
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is not None

    def test_unarchived_user_inherits_join_request_consent(self, api_client, vettor_headers):
        archived = User.objects.create_user(
            phone_number="+12025550702",
            first_name="Old",
            last_name="Member",
        )
        archived.archived_at = timezone.now()
        archived.guidelines_consent_at = None
        archived.sms_consent_at = None
        archived.save(update_fields=["archived_at", "guidelines_consent_at", "sms_consent_at"])

        jr = JoinRequest.objects.create(
            first_name="Old",
            last_name="Member",
            phone_number="+12025550702",
            email="oldmember@example.com",
            sms_consent_at=timezone.now(),
            guidelines_consent_at=timezone.now(),
        )
        resp = api_client.patch(
            f"/api/community/join-requests/{jr.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        assert resp.status_code == 200, resp.content

        archived.refresh_from_db()
        assert archived.archived_at is None
        assert archived.guidelines_consent_at is not None
        assert archived.sms_consent_at is not None
