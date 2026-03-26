import pytest
from community.models import CommunityGuidelines
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_guidelines_user(db):
    from users.models import User

    user = User.objects.create_user(
        email="editor@pda.org",
        password="editorpass123",
    )
    role = Role.objects.create(
        name="guidelines_editor", permissions=[PermissionKey.MANAGE_GUIDELINES]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_guidelines_headers(manage_guidelines_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_guidelines_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.mark.django_db
class TestGetGuidelines:
    def test_get_guidelines_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/guidelines/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "updated_at" in data

    def test_get_guidelines_unauthenticated(self, api_client):
        response = api_client.get("/api/community/guidelines/")
        assert response.status_code == 401

    def test_get_guidelines_returns_existing_content(self, api_client, auth_headers, db):
        g = CommunityGuidelines.get()
        g.content = "# Welcome\n\nBe kind."
        g.save()

        response = api_client.get("/api/community/guidelines/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["content"] == "# Welcome\n\nBe kind."


@pytest.mark.django_db
class TestUpdateGuidelines:
    def test_update_guidelines_with_permission(self, api_client, manage_guidelines_headers):
        payload = {"content": "# Community Guidelines\n\nBe excellent to each other."}
        response = api_client.patch(
            "/api/community/guidelines/",
            data=payload,
            content_type="application/json",
            **manage_guidelines_headers,
        )
        assert response.status_code == 200
        assert "# Community Guidelines" in response.json()["content"]
        assert CommunityGuidelines.get().content == payload["content"]

    def test_update_guidelines_without_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/guidelines/",
            data={"content": "sneaky edit"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_guidelines_unauthenticated(self, api_client):
        response = api_client.patch(
            "/api/community/guidelines/",
            data={"content": "sneaky edit"},
            content_type="application/json",
        )
        assert response.status_code == 401
