import json

import pytest
from community.models import CommunityGuidelines
from users.permissions import PermissionKey
from users.roles import Role


def _pm(text: str) -> str:
    return json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    )


@pytest.fixture
def manage_guidelines_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+15550002001",
        password="editorpass123",
        display_name="Guidelines Editor",
    )
    role = Role.objects.create(
        name="guidelines_editor", permissions=[PermissionKey.EDIT_GUIDELINES]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_guidelines_headers(manage_guidelines_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_guidelines_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


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
        payload = {"content_pm": _pm("Community Guidelines")}
        response = api_client.patch(
            "/api/community/guidelines/",
            data=payload,
            content_type="application/json",
            **manage_guidelines_headers,
        )
        assert response.status_code == 200
        assert "Community Guidelines" in response.json()["content_html"]
        assert CommunityGuidelines.get().content_pm == payload["content_pm"]

    def test_update_guidelines_without_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/guidelines/",
            data={"content_pm": _pm("sneaky edit")},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_guidelines_unauthenticated(self, api_client):
        response = api_client.patch(
            "/api/community/guidelines/",
            data={"content_pm": _pm("sneaky edit")},
            content_type="application/json",
        )
        assert response.status_code == 401
