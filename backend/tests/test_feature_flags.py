import pytest
from community.models import FeatureFlag, FeatureFlagState, resolve_flags
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_flags_user(db):
    user = User.objects.create_user(
        phone_number="+15550002002",
        password="flagseditorpass123",
        first_name="Flags",
        last_name="Editor",
    )
    role = Role.objects.create(
        name="flags_editor", permissions=[PermissionKey.MANAGE_FEATURE_FLAGS]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_flags_headers(manage_flags_user):
    refresh = RefreshToken.for_user(manage_flags_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGetFeatureFlags:
    def test_get_flags_unauthenticated(self, api_client):
        response = api_client.get("/api/community/feature-flags/")
        assert response.status_code == 200
        assert response.json()["flags"][FeatureFlag.EXAMPLE_FLAG] is False

    def test_get_flags_resolves_db_override(self, api_client, db):
        FeatureFlagState.objects.create(key=FeatureFlag.EXAMPLE_FLAG, enabled=True)
        response = api_client.get("/api/community/feature-flags/")
        assert response.json()["flags"][FeatureFlag.EXAMPLE_FLAG] is True

    def test_resolve_flags_ignores_unknown_keys(self, db):
        FeatureFlagState.objects.create(key="not_a_real_flag", enabled=True)
        assert "not_a_real_flag" not in resolve_flags()


@pytest.mark.django_db
class TestUpdateFeatureFlag:
    def test_update_flag_with_permission(self, api_client, manage_flags_headers, settings):
        settings.FLAG_TOGGLING_ALLOWED = True
        response = api_client.patch(
            f"/api/community/feature-flags/{FeatureFlag.EXAMPLE_FLAG}/",
            data={"enabled": True},
            content_type="application/json",
            **manage_flags_headers,
        )
        assert response.status_code == 200
        assert response.json()["flags"][FeatureFlag.EXAMPLE_FLAG] is True
        assert FeatureFlagState.objects.get(key=FeatureFlag.EXAMPLE_FLAG).enabled is True

    def test_update_flag_without_permission(self, api_client, auth_headers, settings):
        settings.FLAG_TOGGLING_ALLOWED = True
        response = api_client.patch(
            f"/api/community/feature-flags/{FeatureFlag.EXAMPLE_FLAG}/",
            data={"enabled": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_flag_unauthenticated(self, api_client):
        response = api_client.patch(
            f"/api/community/feature-flags/{FeatureFlag.EXAMPLE_FLAG}/",
            data={"enabled": True},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_flag_blocked_on_production(self, api_client, manage_flags_headers, settings):
        settings.FLAG_TOGGLING_ALLOWED = False
        response = api_client.patch(
            f"/api/community/feature-flags/{FeatureFlag.EXAMPLE_FLAG}/",
            data={"enabled": True},
            content_type="application/json",
            **manage_flags_headers,
        )
        assert response.status_code == 403

    def test_update_unknown_flag_404s(self, api_client, manage_flags_headers, settings):
        settings.FLAG_TOGGLING_ALLOWED = True
        response = api_client.patch(
            "/api/community/feature-flags/not_a_real_flag/",
            data={"enabled": True},
            content_type="application/json",
            **manage_flags_headers,
        )
        assert response.status_code == 404
