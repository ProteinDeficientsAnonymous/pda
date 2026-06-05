"""Tests for POST /api/auth/accept-guidelines/ — the consent-gate escape hatch.

Stamps guidelines_consent_at on the current user, which clears the hard gate
enforced by config.auth.GatedJWTAuth.
"""

import pytest
from ninja_jwt.tokens import RefreshToken


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


@pytest.mark.django_db
class TestAcceptGuidelines:
    def test_stamps_consent_and_clears_flag(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550401", password="pass", display_name="Consenter"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])

        resp = api_client.post("/api/auth/accept-guidelines/", **_headers(user))
        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_guidelines_consent"] is False

        user.refresh_from_db()
        assert user.guidelines_consent_at is not None

    def test_after_consent_protected_endpoints_unblock(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550402", password="pass", display_name="Consenter"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])
        headers = _headers(user)

        # Blocked before consent.
        assert api_client.get("/api/notifications/", **headers).status_code == 403
        # Consent.
        assert api_client.post("/api/auth/accept-guidelines/", **headers).status_code == 200
        # Unblocked after.
        assert api_client.get("/api/notifications/", **headers).status_code == 200

    def test_idempotent_restamps(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550403", password="pass", display_name="Consenter"
        )
        first = user.guidelines_consent_at  # stamped by conftest default

        resp = api_client.post("/api/auth/accept-guidelines/", **_headers(user))
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.guidelines_consent_at is not None
        assert user.guidelines_consent_at >= first

    def test_requires_auth(self, api_client):
        resp = api_client.post("/api/auth/accept-guidelines/")
        assert resp.status_code == 401

    def test_admin_is_not_grandfathered(self, api_client):
        """Admins are gated too — a fresh admin with null consent is blocked."""
        from users.models import User
        from users.roles import Role

        admin = User.objects.create_user(
            phone_number="+12025550404", password="pass", display_name="Admin"
        )
        admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"is_default": True})
        admin.roles.add(admin_role)
        admin.guidelines_consent_at = None
        admin.save(update_fields=["guidelines_consent_at"])

        assert api_client.get("/api/notifications/", **_headers(admin)).status_code == 403
        assert api_client.post("/api/auth/accept-guidelines/", **_headers(admin)).status_code == 200
