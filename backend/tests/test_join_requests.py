"""Tests for join request submission and management."""

import pytest
from community.models import JoinRequestStatus
from users.permissions import PermissionKey
from users.roles import Role

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def why_join_id(db):
    from community.models import JoinFormQuestion

    q = JoinFormQuestion.objects.filter(required=True).first()
    return str(q.id) if q else ""


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJoinRequestSubmission:
    def test_submit_join_request(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "I want to connect with other vegans."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Leafy G"
        assert data["phone_number"] == "+12025551234"
        assert len(data["answers"]) >= 1

    def test_submit_join_request_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy123",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_phone(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "not-a-number",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_optional_answers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+13105551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_join_request_sends_email_when_vetting_email_set(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = "vetting@pda.org"
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 1
        assert "Test Person" in mail.outbox[0].subject
        assert mail.outbox[0].to == ["vetting@pda.org"]

    def test_join_request_no_email_when_vetting_email_unset(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = ""
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 0

    def test_submit_empty_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "   ",
                "phone_number": "+12025550701",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice",
                "phone_number": "+12025550702",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_too_long(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "A" * 65,
                "phone_number": "+12025550703",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_with_numbers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice2",
                "phone_number": "+12025550704",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_default_status_is_pending(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "New Sprout",
                "phone_number": "+19175551234",
                "answers": {why_join_id: "Collective liberation matters."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == JoinRequestStatus.PENDING


# ---------------------------------------------------------------------------
# Management (list, approve, reject)
# ---------------------------------------------------------------------------


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
        assert "already been approved" in response.json()["detail"]

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
        # Make join request phone match an existing user
        sample_join_request.phone_number = test_user.phone_number
        sample_join_request.save()
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        # No magic token since no user was created
        assert response.json()["magic_link_token"] is None
