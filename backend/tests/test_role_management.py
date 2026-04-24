import pytest
from community._validation import Code
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code


@pytest.fixture
def manage_users_user(db):
    """Non-superuser with manage_users + manage_roles permissions."""
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550002",
        password="managerpass123",
        display_name="Manager",
    )
    role = Role.objects.create(
        name="manager", permissions=[PermissionKey.MANAGE_USERS, PermissionKey.MANAGE_ROLES]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_users_headers(manage_users_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_users_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestRoleManagementAPI:
    def test_list_roles_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/auth/roles/", **auth_headers)
        assert response.status_code == 200
        names = [r["name"] for r in response.json()]
        assert "admin" in names
        assert "member" in names

    def test_list_roles_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/roles/")
        assert response.status_code == 401

    def test_create_role_success(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "vettor", "permissions": [PermissionKey.APPROVE_JOIN_REQUESTS]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "vettor"

    def test_create_role_requires_manage_roles(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "newrole"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_create_role_duplicate_name(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "member"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400

    def test_patch_role_permissions(self, api_client, manage_users_headers):
        role = Role.objects.create(name="custom", permissions=[])
        response = api_client.patch(
            f"/api/auth/roles/{role.id}/",
            {"permissions": [PermissionKey.MANAGE_EVENTS]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        assert PermissionKey.MANAGE_EVENTS in response.json()["permissions"]

    def test_patch_default_role_blocked(self, api_client, manage_users_headers):
        admin_role = Role.objects.get(name="admin")
        response = api_client.patch(
            f"/api/auth/roles/{admin_role.id}/",
            {"name": "superadmin"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Role.PROTECTED_CANNOT_EDIT)

    def test_patch_default_role_permissions_blocked(self, api_client, manage_users_headers):
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/roles/{member_role.id}/",
            {"permissions": [PermissionKey.MANAGE_EVENTS]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Role.PROTECTED_CANNOT_EDIT)
        member_role.refresh_from_db()
        assert PermissionKey.MANAGE_EVENTS not in member_role.permissions

    def test_delete_role_success(self, api_client, manage_users_headers):
        role = Role.objects.create(name="deleteme", permissions=[])
        response = api_client.delete(f"/api/auth/roles/{role.id}/", **manage_users_headers)
        assert response.status_code == 204

    def test_delete_protected_role_blocked(self, api_client, manage_users_headers):
        admin_role = Role.objects.get(name="admin")
        response = api_client.delete(f"/api/auth/roles/{admin_role.id}/", **manage_users_headers)
        assert response.status_code == 400
        assert_error_code(response, Code.Role.PROTECTED_CANNOT_DELETE)

    def test_delete_role_with_users_succeeds(self, api_client, manage_users_headers, test_user):
        role = Role.objects.create(name="occupied", permissions=[])
        test_user.roles.add(role)
        response = api_client.delete(f"/api/auth/roles/{role.id}/", **manage_users_headers)
        assert response.status_code == 204
        assert not Role.objects.filter(pk=role.id).exists()
        assert not test_user.roles.filter(name="occupied").exists()

    def test_list_roles_includes_user_count(self, api_client, auth_headers, test_user):
        role = Role.objects.create(name="popular", permissions=[])
        test_user.roles.add(role)
        response = api_client.get("/api/auth/roles/", **auth_headers)
        assert response.status_code == 200
        popular = next(r for r in response.json() if r["name"] == "popular")
        assert popular["user_count"] == 1
