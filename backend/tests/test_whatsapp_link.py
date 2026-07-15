import pytest
from community.models import WhatsAppLinkConfig
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def edit_whatsapp_link_user(db):
    user = User.objects.create_user(
        phone_number="+15550003003",
        password="vetterpass123",
        first_name="Link",
        last_name="Editor",
    )
    role = Role.objects.create(
        name="whatsapp_link_editor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_whatsapp_link_headers(edit_whatsapp_link_user):
    refresh = RefreshToken.for_user(edit_whatsapp_link_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGetWhatsAppLink:
    def test_authenticated_user_sees_empty_default(self, api_client, auth_headers):
        response = api_client.get("/api/community/whatsapp-link/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["link"] == ""
        assert "updated_at" in data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/community/whatsapp-link/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestUpdateWhatsAppLink:
    def test_with_permission_updates_link(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://chat.whatsapp.com/abc123"},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 200
        assert response.json()["link"] == "https://chat.whatsapp.com/abc123"
        assert WhatsAppLinkConfig.get().link == "https://chat.whatsapp.com/abc123"

    def test_accepts_wa_me_link(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://wa.me/1234567890"},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 200
        assert response.json()["link"] == "https://wa.me/1234567890"

    def test_can_be_cleared(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": ""},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 200
        assert response.json()["link"] == ""

    def test_without_permission_returns_403(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://chat.whatsapp.com/abc123"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, "perm.denied")

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://chat.whatsapp.com/abc123"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_non_whatsapp_host_rejected(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://example.com/group"},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, "url.whatsapp_not_recognized", expected_field="link")

    def test_bare_domain_without_path_rejected(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://chat.whatsapp.com"},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, "url.path_required", expected_field="link")

    def test_too_long_link_rejected(self, api_client, edit_whatsapp_link_headers):
        response = api_client.patch(
            "/api/community/whatsapp-link/",
            data={"link": "https://chat.whatsapp.com/" + "x" * 250},
            content_type="application/json",
            **edit_whatsapp_link_headers,
        )
        assert response.status_code == 422
        entry = assert_error_code(response, "url.too_long", expected_field="link")
        assert entry["params"]["max_length"] == 200
