import pytest
from community._validation import Code, ValidationException
from ninja_jwt.tokens import RefreshToken
from users.api import (
    _create_user_with_role,
    _validate_admin_role_change,
    _validate_member_role_required,
)
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        phone_number="+12025550001",
        password="adminpass123",
        display_name="Admin User",
    )
    return user


@pytest.fixture
def admin_headers(admin_user):
    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_users_user(db):
    """A non-superuser with only manage_users permission."""
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
        assert "refresh" not in data

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
        superuser = User.objects.create_superuser(
            phone_number="+12025559999", password="superpass123"
        )
        assert superuser.roles.filter(name="admin").exists()

    def test_has_permission_uses_prefetch_cache(self, test_user):
        member_role = Role.objects.get(name="member")
        test_user.roles.add(member_role)
        user = User.objects.prefetch_related("roles").get(pk=test_user.pk)
        assert not user.has_permission(PermissionKey.MANAGE_USERS)

    @pytest.mark.parametrize("bad_value", ["manage_events", {"manage_events": True}, 42])
    def test_corrupt_permissions_shape_grants_no_permissions(self, test_user, bad_value):
        role = Role.objects.get(name="member")
        Role.objects.filter(pk=role.pk).update(permissions=bad_value)
        role.refresh_from_db()
        test_user.roles.add(role)
        assert role.effective_permissions == []
        assert not test_user.has_permission(PermissionKey.MANAGE_EVENTS)

    def test_corrupt_permissions_filters_non_string_entries(self, test_user):
        role = Role.objects.get(name="member")
        Role.objects.filter(pk=role.pk).update(
            permissions=[PermissionKey.MANAGE_EVENTS, None, 7, {"x": 1}]
        )
        role.refresh_from_db()
        test_user.roles.add(role)
        assert role.effective_permissions == [PermissionKey.MANAGE_EVENTS]
        assert test_user.has_permission(PermissionKey.MANAGE_EVENTS)


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
        assert response.status_code == 409
        assert_error_code(response, Code.Phone.ALREADY_EXISTS)

    def test_create_user_assigns_member_role_by_default(self, api_client, admin_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12125551234"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
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
        assert_error_code(response, Code.User.CANNOT_DELETE_SELF)

    def test_delete_user_cannot_delete_last_admin(
        self, api_client, manage_users_headers, admin_user
    ):
        response = api_client.delete(
            f"/api/auth/users/{admin_user.id}/",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.User.CANNOT_DELETE_LAST_ADMIN)

    def test_delete_user_success(self, api_client, admin_headers):
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
        assert_error_code(response, Code.Role.CANNOT_REMOVE_OWN_ADMIN)

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
        assert_error_code(response, Code.Role.MEMBER_ROLE_REQUIRED)
        assert test_user.roles.filter(name="member").exists()


# ---------------------------------------------------------------------------
# Unit tests for _create_user_with_role helper
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateUserWithRole:
    def _requester(self):
        return User.objects.create_user(phone_number="+12025550000", password="p")

    def test_creates_user_with_default_member_role(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        user, magic_token = _create_user_with_role(
            "+12025559999", "Test", "User", "t@e.com", None, requesting_user=self._requester()
        )
        assert user.phone_number == "+12025559999"
        assert len(magic_token) == 36  # UUID format
        assert user.roles.filter(name="member").exists()

    def test_creates_user_with_specific_role(self):
        role = Role.objects.create(name="custom_role")
        user, _ = _create_user_with_role(
            "+12025558888",
            "Custom",
            "User",
            "c@e.com",
            str(role.pk),
            requesting_user=self._requester(),
        )
        assert user.roles.filter(pk=role.pk).exists()

    def test_raises_on_duplicate_phone(self):
        User.objects.create_user(phone_number="+12025557777", password="pass123")
        with pytest.raises(ValidationException) as exc_info:
            _create_user_with_role(
                "+12025557777", "Dup", "", None, None, requesting_user=self._requester()
            )
        assert exc_info.value.code == Code.Phone.ALREADY_EXISTS

    def test_raises_on_invalid_phone(self):
        with pytest.raises(ValidationException) as exc_info:
            _create_user_with_role(
                "not-a-phone", "Bad", "Phone", None, None, requesting_user=self._requester()
            )
        assert exc_info.value.code == Code.Phone.INVALID

    def test_raises_on_bad_role_and_deletes_user(self):
        with pytest.raises(ValidationException) as exc_info:
            _create_user_with_role(
                "+12025556666",
                "Bad Role",
                "User",
                "b@e.com",
                "00000000-0000-0000-0000-000000000000",
                requesting_user=self._requester(),
            )
        assert exc_info.value.code == Code.Role.NOT_FOUND
        assert not User.objects.filter(phone_number="+12025556666").exists()

    def test_raises_when_non_admin_grants_admin_role(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        non_admin = self._requester()
        with pytest.raises(ValidationException) as exc_info:
            _create_user_with_role(
                "+12025554444",
                "Sneaky",
                "Admin",
                None,
                str(admin_role.pk),
                requesting_user=non_admin,
            )
        assert exc_info.value.code == Code.Role.CANNOT_GRANT_ADMIN
        assert exc_info.value.status_code == 403
        assert not User.objects.filter(phone_number="+12025554444").exists()

    def test_admin_can_grant_admin_role(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        requester = self._requester()
        requester.roles.add(admin_role)
        user, _ = _create_user_with_role(
            "+12025553333",
            "New",
            "Admin",
            None,
            str(admin_role.pk),
            requesting_user=requester,
        )
        assert user.roles.filter(pk=admin_role.pk).exists()


# ---------------------------------------------------------------------------
# Unit tests for _validate_admin_role_change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateAdminRoleChange:
    def _admin_requester(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        requester = User.objects.create_user(phone_number="+12025559000", password="p")
        requester.roles.add(admin_role)
        return requester

    def test_returns_none_when_no_admin_role_exists(self):
        user = User.objects.create_user(phone_number="+12025550101", password="p", email="a@e.com")
        other = User.objects.create_user(phone_number="+12025550199", password="p")
        # No admin role exists — should be a no-op (not raise)
        _validate_admin_role_change(user, other, [])

    def test_returns_error_when_removing_own_admin(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550102", password="p", email="b@e.com")
        user.roles.add(admin_role)
        with pytest.raises(ValidationException) as exc_info:
            _validate_admin_role_change(user, user, [member_role])
        assert exc_info.value.code == Code.Role.CANNOT_REMOVE_OWN_ADMIN

    def test_returns_none_when_keeping_own_admin(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550103", password="p", email="c@e.com")
        user.roles.add(admin_role)
        # Keeping admin — no-op
        _validate_admin_role_change(user, user, [admin_role])

    def test_returns_error_when_removing_last_admin(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550104", password="p", email="d@e.com")
        user.roles.add(admin_role)
        # Request from a different user (not self-removal). The requester is not
        # an admin, so ``user`` remains the sole/last admin.
        requester = User.objects.create_user(phone_number="+12025550144", password="p")
        with pytest.raises(ValidationException) as exc_info:
            _validate_admin_role_change(user, requester, [member_role])
        assert exc_info.value.code == Code.Role.CANNOT_REMOVE_LAST_ADMIN

    def test_returns_error_when_non_admin_grants_admin(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        target = User.objects.create_user(phone_number="+12025550105", password="p")
        non_admin = User.objects.create_user(phone_number="+12025550106", password="p")
        with pytest.raises(ValidationException) as exc_info:
            _validate_admin_role_change(target, non_admin, [admin_role])
        assert exc_info.value.code == Code.Role.CANNOT_GRANT_ADMIN
        assert exc_info.value.status_code == 403

    def test_admin_may_grant_admin(self):
        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        target = User.objects.create_user(phone_number="+12025550107", password="p")
        # Admin requester granting admin to target — no-op (no raise)
        _validate_admin_role_change(target, self._admin_requester(), [admin_role])


# ---------------------------------------------------------------------------
# Unit tests for _validate_member_role_required
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateMemberRoleRequired:
    def test_returns_none_when_member_role_present(self):
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        custom = Role.objects.create(name="greeter")
        # Member present — no-op
        _validate_member_role_required([member_role, custom])

    def test_returns_error_when_member_role_missing(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        custom = Role.objects.create(name="greeter")
        with pytest.raises(ValidationException) as exc_info:
            _validate_member_role_required([custom])
        assert exc_info.value.code == Code.Role.MEMBER_ROLE_REQUIRED

    def test_returns_error_when_new_roles_empty(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        with pytest.raises(ValidationException) as exc_info:
            _validate_member_role_required([])
        assert exc_info.value.code == Code.Role.MEMBER_ROLE_REQUIRED
