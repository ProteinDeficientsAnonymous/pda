import pytest

from users.permissions import PermissionKey
from users.roles import Role


@pytest.mark.django_db
class TestAuth:
    def test_login_valid(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "member@pda.org", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_invalid(self, api_client):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "nobody@pda.org", "password": "wrong"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_me_authenticated(self, api_client, test_user, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "member@pda.org"

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestJoinRequest:
    def test_submit_join_request(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "name": "Leafy Green",
                "email": "leafy@vegan.org",
                "pronouns": "they/them",
                "how_they_heard": "Word of mouth",
                "why_join": "I want to connect with other vegans in collective liberation work.",
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Leafy Green"

    def test_submit_join_request_missing_fields(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {"name": "Leafy", "email": "leafy@vegan.org"},
            content_type="application/json",
        )
        # Django Ninja returns 422 for Pydantic validation errors (missing required fields)
        assert response.status_code == 422


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
            email="super@pda.org", password="superpass123"
        )
        assert superuser.roles.filter(name="admin").exists()

    def test_has_permission_uses_prefetch_cache(self, test_user):
        from django.test.utils import override_settings
        from users.models import User

        member_role = Role.objects.get(name="member")
        test_user.roles.add(member_role)
        # Simulate prefetch by fetching with prefetch_related
        user = User.objects.prefetch_related("roles").get(pk=test_user.pk)
        # Access prefetch cache path
        assert not user.has_permission(PermissionKey.MANAGE_USERS)


@pytest.mark.django_db
class TestEvents:
    def test_events_requires_auth(self, api_client):
        response = api_client.get("/api/community/events/")
        assert response.status_code == 401

    def test_events_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
