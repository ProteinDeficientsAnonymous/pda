import pytest
from community.models import TentativeApprovalMessageTemplate
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def edit_tentative_message_user(db):
    user = User.objects.create_user(
        phone_number="+15550003002",
        password="vetterpass123",
        first_name="Vetter",
        last_name="Two",
    )
    role = Role.objects.create(
        name="tentative_message_editor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_tentative_message_headers(edit_tentative_message_user):
    refresh = RefreshToken.for_user(edit_tentative_message_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGetTentativeApprovalMessage:
    def test_authenticated_user_sees_default_empty_body(self, api_client, auth_headers):
        response = api_client.get("/api/community/tentative-approval-message/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == ""
        assert "updated_at" in data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/community/tentative-approval-message/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestUpdateTentativeApprovalMessage:
    def test_with_permission_updates_body(self, api_client, edit_tentative_message_headers):
        response = api_client.patch(
            "/api/community/tentative-approval-message/",
            data={"body": "hi ${FIRST_NAME}, thanks for coming out — you're a full member now"},
            content_type="application/json",
            **edit_tentative_message_headers,
        )
        assert response.status_code == 200
        assert "${FIRST_NAME}" in response.json()["body"]
        assert (
            TentativeApprovalMessageTemplate.get().body
            == "hi ${FIRST_NAME}, thanks for coming out — you're a full member now"
        )

    def test_without_permission_returns_403(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/tentative-approval-message/",
            data={"body": "sneaky edit"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(
            "/api/community/tentative-approval-message/",
            data={"body": "sneaky edit"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_empty_body_rejected(self, api_client, edit_tentative_message_headers):
        response = api_client.patch(
            "/api/community/tentative-approval-message/",
            data={"body": "   "},
            content_type="application/json",
            **edit_tentative_message_headers,
        )
        assert response.status_code == 422
        assert_error_code(
            response, "tentative_approval_message.body_required", expected_field="body"
        )

    def test_too_long_body_rejected(self, api_client, edit_tentative_message_headers):
        response = api_client.patch(
            "/api/community/tentative-approval-message/",
            data={"body": "x" * 5000},
            content_type="application/json",
            **edit_tentative_message_headers,
        )
        assert response.status_code == 422
        entry = assert_error_code(
            response, "tentative_approval_message.body_too_long", expected_field="body"
        )
        assert entry["params"]["max_length"] == 4000
