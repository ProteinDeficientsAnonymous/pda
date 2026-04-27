import pytest
from community.models import WelcomeMessageTemplate
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def edit_welcome_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+15550003001",
        password="vetterpass123",
        display_name="Welcome Editor",
    )
    role = Role.objects.create(
        name="welcome_editor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_welcome_headers(edit_welcome_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_welcome_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGetWelcomeTemplate:
    def test_authenticated_user_sees_seeded_body(self, api_client, auth_headers):
        response = api_client.get("/api/community/welcome-template/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Migration 0050 seeds the verbose template from issue #375
        assert "${NAME}" in data["body"]
        assert "${SENDER_NAME}" in data["body"]
        assert "${MAGIC_LINK}" in data["body"]
        assert "updated_at" in data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/community/welcome-template/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestUpdateWelcomeTemplate:
    def test_with_permission_updates_body(self, api_client, edit_welcome_headers):
        response = api_client.patch(
            "/api/community/welcome-template/",
            data={"body": "hi ${NAME}, welcome — sign in: ${MAGIC_LINK}"},
            content_type="application/json",
            **edit_welcome_headers,
        )
        assert response.status_code == 200
        assert "${NAME}" in response.json()["body"]
        assert WelcomeMessageTemplate.get().body == "hi ${NAME}, welcome — sign in: ${MAGIC_LINK}"

    def test_without_permission_returns_403(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/welcome-template/",
            data={"body": "sneaky edit"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(
            "/api/community/welcome-template/",
            data={"body": "sneaky edit"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_empty_body_rejected(self, api_client, edit_welcome_headers):
        response = api_client.patch(
            "/api/community/welcome-template/",
            data={"body": "   "},
            content_type="application/json",
            **edit_welcome_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, "welcome_template.body_required", expected_field="body")

    def test_too_long_body_rejected(self, api_client, edit_welcome_headers):
        response = api_client.patch(
            "/api/community/welcome-template/",
            data={"body": "x" * 5000},
            content_type="application/json",
            **edit_welcome_headers,
        )
        assert response.status_code == 422
        entry = assert_error_code(response, "welcome_template.body_too_long", expected_field="body")
        assert entry["params"]["max_length"] == 4000
