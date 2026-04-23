"""Tests for join request management (list, approve, reject)."""

import pytest
from community._validation import Code
from community.models import JoinRequestStatus
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def vettor_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550003",
        password="vettorpass123",
        display_name="Vettor",
    )
    role = Role.objects.create(name="vettor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
    user.roles.add(role)
    return user


@pytest.fixture
def vettor_headers(vettor_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(vettor_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def sample_join_request(db):
    from community.models import JoinFormQuestion, JoinRequest

    q = JoinFormQuestion.objects.filter(required=True).first()
    answers = {}
    if q:
        answers[str(q.id)] = {"label": q.label, "answer": "I believe in collective liberation."}
    return JoinRequest.objects.create(
        display_name="Sprout Seedling",
        phone_number="+16505551234",
        custom_answers=answers,
    )


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
        assert data[0]["display_name"] == "Sprout Seedling"
        assert data[0]["status"] == JoinRequestStatus.PENDING

    def test_admin_can_access_list(self, api_client, db):
        from users.models import User

        admin = User.objects.create_superuser(
            phone_number="+12025550001",
            password="adminpass123",
            display_name="Admin User",
        )
        from ninja_jwt.tokens import RefreshToken

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
        from users.models import User

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
        assert user.display_name == "Sprout Seedling"
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
        import uuid

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
        from users.models import User

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

    def test_list_excludes_approved_onboarded_user(
        self, api_client, vettor_headers, sample_join_request
    ):
        from users.models import User

        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.needs_onboarding = False
        user.save(update_fields=["needs_onboarding"])

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
        ids = [r["id"] for r in response.json()]
        assert str(sample_join_request.id) in ids

    def test_list_flags_previously_archived(self, api_client, vettor_headers, db):
        from community.models import JoinRequest
        from django.utils import timezone
        from users.models import User

        archived = User.objects.create_user(
            phone_number="+12025550150", display_name="Comeback Kid"
        )
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])
        jr = JoinRequest.objects.create(
            display_name="Comeback Kid",
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
        from community.models import JoinRequest
        from django.utils import timezone
        from users.models import User

        archived = User.objects.create_user(phone_number="+12025550151", display_name="Phoenix")
        archived.archived_at = timezone.now()
        archived.needs_onboarding = False
        archived.save(update_fields=["archived_at", "needs_onboarding"])

        jr = JoinRequest.objects.create(
            display_name="Phoenix",
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

    def test_list_keeps_pending_and_rejected_unaffected(self, api_client, vettor_headers, db):
        from community.models import JoinRequest
        from users.models import User

        pending = JoinRequest.objects.create(
            display_name="Pending Person",
            phone_number="+12025550101",
            status=JoinRequestStatus.PENDING,
        )
        rejected = JoinRequest.objects.create(
            display_name="Rejected Person",
            phone_number="+12025550102",
            status=JoinRequestStatus.REJECTED,
        )
        approved = JoinRequest.objects.create(
            display_name="Onboarded Person",
            phone_number="+12025550103",
            status=JoinRequestStatus.APPROVED,
        )
        User.objects.create_user(
            phone_number="+12025550103",
            display_name="Onboarded Person",
            needs_onboarding=False,
        )

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        ids = [r["id"] for r in response.json()]
        assert str(pending.id) in ids
        assert str(rejected.id) in ids
        assert str(approved.id) not in ids
