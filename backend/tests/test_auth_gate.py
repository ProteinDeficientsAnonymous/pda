"""Tests for GatedJWTAuth — per-request enforcement of account state.

A valid JWT outlives the state changes that should revoke access (unusable
password, pause, archive). GatedJWTAuth re-checks on every protected request and
403s, except for the allowlist a pending user needs to resolve their state.
"""

import pytest
from ninja_jwt.tokens import RefreshToken


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


@pytest.mark.django_db
class TestGatedJWTAuth:
    def test_needs_password_reset_blocks_protected_endpoint(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550301", password="pass", display_name="Reset Me"
        )
        user.needs_password_reset = True
        user.save(update_fields=["needs_password_reset"])

        # A normal protected endpoint (not on the allowlist) → 403.
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.password_reset_required"

    def test_needs_password_reset_allows_me(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550302", password="pass", display_name="Reset Me"
        )
        user.needs_password_reset = True
        user.save(update_fields=["needs_password_reset"])

        # /me/ is allowlisted so the frontend can read the flag and route.
        resp = api_client.get("/api/auth/me/", **_headers(user))
        assert resp.status_code == 200
        assert resp.json()["needs_password_reset"] is True

    def test_needs_password_reset_allows_complete_onboarding(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550303",
            password="pass",
            display_name="Reset Me",
            email="reset@example.com",
        )
        user.needs_password_reset = True
        user.set_unusable_password()
        user.save(update_fields=["needs_password_reset", "password"])

        # The escape hatch must stay reachable.
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "FreshPass123!"},
            content_type="application/json",
            **_headers(user),
        )
        assert resp.status_code == 200, resp.content
        user.refresh_from_db()
        assert user.needs_password_reset is False

    def test_needs_onboarding_blocks_protected_endpoint(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550304", password="pass", display_name="", needs_onboarding=True
        )
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.onboarding_required"

    def test_paused_user_blocked_on_protected_endpoint_after_token_issued(self, api_client):
        """is_paused set AFTER a token was issued must still revoke access per-request."""
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550305", password="pass", display_name="Paused"
        )
        headers = _headers(user)  # token minted while active
        user.is_paused = True
        user.save(update_fields=["is_paused"])

        resp = api_client.get("/api/notifications/", **headers)
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.account_paused"

    def test_archived_user_blocked_on_protected_endpoint_after_token_issued(self, api_client):
        from django.utils import timezone
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550306", password="pass", display_name="Archived"
        )
        headers = _headers(user)
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])

        resp = api_client.get("/api/notifications/", **headers)
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == "auth.account_archived"

    def test_normal_user_unaffected(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550307", password="pass", display_name="Normal"
        )
        resp = api_client.get("/api/notifications/", **_headers(user))
        assert resp.status_code == 200
