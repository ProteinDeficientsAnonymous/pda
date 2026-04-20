import pytest
from users.api import (
    _create_user_with_role,
    _validate_admin_role_change,
    _validate_member_role_required,
)
from users.permissions import PermissionKey
from users.roles import Role

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    from users.models import User

    user = User.objects.create_superuser(
        phone_number="+12025550001",
        password="adminpass123",
        display_name="Admin User",
    )
    return user


@pytest.fixture
def admin_headers(admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_users_user(db):
    """A non-superuser with only manage_users permission."""
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


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuth:
    def test_login_valid(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_invalid(self, api_client):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+19999999999", "password": "wrong"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_old_email_format_rejected(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "member@pda.org", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_me_authenticated(self, api_client, test_user, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "+12025550101"
        assert data["display_name"] == "Test Member"
        assert "first_name" not in data
        assert "last_name" not in data
        assert "roles" in data

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Roles and permissions (model-level)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRolesAndPermissions:
    def test_has_permission_via_role(self, test_user):
        role = Role.objects.get(name="member")
        role.permissions = [PermissionKey.MANAGE_EVENTS]
        role.save()
        test_user.roles.add(role)
        assert test_user.has_permission(PermissionKey.MANAGE_EVENTS)
        assert not test_user.has_permission(PermissionKey.MANAGE_USERS)

    def test_admin_role_grants_all_permissions(self, test_user):
        admin_role = Role.objects.get(name="admin")
        test_user.roles.add(admin_role)
        assert test_user.has_permission(PermissionKey.MANAGE_USERS)
        assert test_user.has_permission(PermissionKey.MANAGE_EVENTS)
        assert test_user.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS)

    def test_no_roles_grants_no_permissions(self, test_user):
        assert not test_user.has_permission(PermissionKey.MANAGE_EVENTS)

    def test_superuser_gets_admin_role_on_create(self, db):
        from users.models import User

        superuser = User.objects.create_superuser(
            phone_number="+12025559999", password="superpass123"
        )
        assert superuser.roles.filter(name="admin").exists()

    def test_has_permission_uses_prefetch_cache(self, test_user):
        from users.models import User

        member_role = Role.objects.get(name="member")
        test_user.roles.add(member_role)
        user = User.objects.prefetch_related("roles").get(pk=test_user.pk)
        assert not user.has_permission(PermissionKey.MANAGE_USERS)


# ---------------------------------------------------------------------------
# User management API (#3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserManagementAPI:
    def test_create_user_requires_permission(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550999"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_create_user_success(self, api_client, admin_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025551234", "display_name": "New Member"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "+12025551234"
        assert "magic_link_token" in data
        assert len(data["magic_link_token"]) == 36  # UUID format

    def test_create_user_duplicate_phone(self, api_client, admin_headers, test_user):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550101"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400

    def test_create_user_assigns_member_role_by_default(self, api_client, admin_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12125551234"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
        from users.models import User

        user = User.objects.get(phone_number="+12125551234")
        assert user.roles.filter(name="member").exists()

    def test_list_users_requires_manage_users(self, api_client, auth_headers):
        response = api_client.get("/api/auth/users/", **auth_headers)
        assert response.status_code == 403

    def test_list_users_success(self, api_client, admin_headers, test_user):
        response = api_client.get("/api/auth/users/", **admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_update_user(self, api_client, admin_headers, test_user):
        response = api_client.patch(
            f"/api/auth/users/{test_user.id}/",
            {"display_name": "Updated Name"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    def test_delete_user_cannot_delete_self(self, api_client, admin_headers, admin_user):
        response = api_client.delete(
            f"/api/auth/users/{admin_user.id}/",
            **admin_headers,
        )
        assert response.status_code == 400
        assert "own account" in response.json()["detail"]

    def test_delete_user_cannot_delete_last_admin(
        self, api_client, manage_users_headers, admin_user
    ):
        response = api_client.delete(
            f"/api/auth/users/{admin_user.id}/",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert "last admin" in response.json()["detail"]

    def test_delete_user_success(self, api_client, admin_headers):
        from users.models import User

        other = User.objects.create_user(phone_number="+12025550888", password="pass123")
        response = api_client.delete(f"/api/auth/users/{other.id}/", **admin_headers)
        assert response.status_code == 204

    def test_update_user_roles_cannot_remove_own_admin(self, api_client, admin_headers, admin_user):
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{admin_user.id}/roles/",
            {"role_ids": [str(member_role.id)]},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert "own admin role" in response.json()["detail"]

    def test_update_user_roles_cannot_remove_member(self, api_client, admin_headers, test_user):
        member_role = Role.objects.get(name="member")
        test_user.roles.add(member_role)
        custom = Role.objects.create(name="greeter", permissions=[])
        response = api_client.patch(
            f"/api/auth/users/{test_user.id}/roles/",
            {"role_ids": [str(custom.id)]},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert "member role" in response.json()["detail"]
        assert test_user.roles.filter(name="member").exists()


# ---------------------------------------------------------------------------
# Unit tests for _create_user_with_role helper
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateUserWithRole:
    def test_creates_user_with_default_member_role(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        user, magic_token = _create_user_with_role("+12025559999", "Test User", "t@e.com", None)
        assert user.phone_number == "+12025559999"
        assert len(magic_token) == 36  # UUID format
        assert user.roles.filter(name="member").exists()

    def test_creates_user_with_specific_role(self):
        role = Role.objects.create(name="custom_role")
        user, _ = _create_user_with_role("+12025558888", "Custom User", "c@e.com", str(role.pk))
        assert user.roles.filter(pk=role.pk).exists()

    def test_raises_on_duplicate_phone(self):
        from users.models import User

        User.objects.create_user(phone_number="+12025557777", password="pass123")
        with pytest.raises(ValueError, match="already exists"):
            _create_user_with_role("+12025557777", "Dup", None, None)

    def test_raises_on_invalid_phone(self):
        with pytest.raises(ValueError):
            _create_user_with_role("not-a-phone", "Bad Phone", None, None)

    def test_raises_on_bad_role_and_deletes_user(self):
        from users.models import User

        with pytest.raises(ValueError, match="Role not found"):
            _create_user_with_role(
                "+12025556666", "Bad Role User", "b@e.com", "00000000-0000-0000-0000-000000000000"
            )
        assert not User.objects.filter(phone_number="+12025556666").exists()


# ---------------------------------------------------------------------------
# Unit tests for _validate_admin_role_change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateAdminRoleChange:
    def test_returns_none_when_no_admin_role_exists(self):
        from users.models import User

        user = User.objects.create_user(phone_number="+12025550101", password="p", email="a@e.com")
        assert _validate_admin_role_change(user, "other-pk", []) is None

    def test_returns_error_when_removing_own_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550102", password="p", email="b@e.com")
        user.roles.add(admin_role)
        result = _validate_admin_role_change(user, str(user.pk), [member_role])
        assert result == "You cannot remove your own admin role."

    def test_returns_none_when_keeping_own_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550103", password="p", email="c@e.com")
        user.roles.add(admin_role)
        assert _validate_admin_role_change(user, str(user.pk), [admin_role]) is None

    def test_returns_error_when_removing_last_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550104", password="p", email="d@e.com")
        user.roles.add(admin_role)
        # Request from a different user (not self-removal)
        result = _validate_admin_role_change(user, "someone-else", [member_role])
        assert result == "Cannot remove admin from the last admin."


# ---------------------------------------------------------------------------
# Unit tests for _validate_member_role_required
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateMemberRoleRequired:
    def test_returns_none_when_member_role_present(self):
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        custom = Role.objects.create(name="greeter")
        assert _validate_member_role_required([member_role, custom]) is None

    def test_returns_error_when_member_role_missing(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        custom = Role.objects.create(name="greeter")
        result = _validate_member_role_required([custom])
        assert result == "Every user must keep the member role."

    def test_returns_error_when_new_roles_empty(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        result = _validate_member_role_required([])
        assert result == "Every user must keep the member role."


# ---------------------------------------------------------------------------
# Role management API (#4)
# ---------------------------------------------------------------------------


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
        assert "built-in" in response.json()["detail"]

    def test_patch_default_role_permissions_blocked(self, api_client, manage_users_headers):
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/roles/{member_role.id}/",
            {"permissions": [PermissionKey.MANAGE_EVENTS]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert "built-in" in response.json()["detail"]
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
        assert "protected" in response.json()["detail"]

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
