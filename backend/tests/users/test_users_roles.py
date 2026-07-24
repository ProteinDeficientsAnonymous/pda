import pytest
from community._validation import Code
from ninja_jwt.tokens import RefreshToken
from tests._asserts import assert_error_code
from users.models import User
from users.roles import Role


@pytest.mark.django_db
class TestUpdateUserRoles:
    def test_manage_users_only_cannot_update_roles(
        self, api_client, manage_users_headers, other_user
    ):
        """MANAGE_USERS alone (a vetter) cannot reassign roles — needs admin (Issue 1152)."""
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id)]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_manage_roles_alone_cannot_update_roles(
        self, api_client, manage_roles_headers, other_user
    ):
        """A non-admin role holding MANAGE_ROLES still cannot reassign roles (Issue 1152)."""
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id)]},
            content_type="application/json",
            **manage_roles_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_admin_can_grant_admin_role(self, api_client, other_user):
        admin_role = Role.objects.get(name="admin")
        member_role = Role.objects.get(name="member")
        admin_user = User.objects.create_user(phone_number="+12025550401", password="adminpass123")
        admin_user.roles.add(admin_role)
        refresh = RefreshToken.for_user(admin_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore

        response = api_client.patch(
            f"/api/auth/users/{other_user.pk}/roles/",
            {"role_ids": [str(member_role.id), str(admin_role.id)]},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        assert other_user.roles.filter(name="admin").exists()
