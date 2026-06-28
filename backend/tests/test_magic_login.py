"""Tests for the magic-login consume endpoint (GET /api/auth/magic-login/{token}/)."""

from datetime import timedelta

import pytest
from community._validation import Code
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import MagicLoginToken, User

from tests._asserts import assert_error_code


@pytest.mark.django_db
class TestMagicLogin:
    def test_magic_login_valid_returns_tokens(self, api_client, test_user):
        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" not in data

    def test_magic_login_invalid_token(self, api_client, db):
        response = api_client.get("/api/auth/magic-login/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 400

    def test_magic_login_used_token(self, api_client, test_user):
        magic = MagicLoginToken.create_for_user(test_user)
        magic.used = True
        magic.save(update_fields=["used"])
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 400

    def test_magic_login_expired_token(self, api_client, test_user):
        magic = MagicLoginToken.objects.create(
            user=test_user,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 400

    def test_magic_login_paused_user_returns_403(self, api_client, test_user):
        test_user.is_paused = True
        test_user.save(update_fields=["is_paused"])
        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_PAUSED)

    def test_magic_login_marks_token_used(self, api_client, test_user):
        magic = MagicLoginToken.create_for_user(test_user)
        api_client.get(f"/api/auth/magic-login/{magic.token}/")
        magic.refresh_from_db()
        assert magic.used is True

    def test_magic_login_cross_user_blocked(self, api_client, test_user):
        """A logged-in user clicking another user's magic link must be rejected."""
        other = User.objects.create_user(
            phone_number="+12025550202", password="otherpass123", display_name="other"
        )
        magic = MagicLoginToken.create_for_user(other)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(test_user).access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/", **headers)
        assert response.status_code == 403
        magic.refresh_from_db()
        assert magic.used is False

    def test_magic_login_same_user_still_works_when_authed(self, api_client, test_user):
        """Clicking your own magic link while already logged in is allowed."""
        magic = MagicLoginToken.create_for_user(test_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(test_user).access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/", **headers)
        assert response.status_code == 200

    def test_self_service_token_forces_password_reset_on_consume(self, api_client, test_user):
        """A requires_password_reset token flags the user and disables the old password."""
        test_user.login_link_requested = True
        test_user.save(update_fields=["login_link_requested"])
        magic = MagicLoginToken.create_for_user(test_user, requires_password_reset=True)

        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200

        test_user.refresh_from_db()
        assert test_user.needs_password_reset is True
        assert test_user.has_usable_password() is False
        # login_link_requested is cleared so future link requests aren't skipped.
        assert test_user.login_link_requested is False

    def test_admin_onboarding_token_does_not_force_password_reset(self, api_client, test_user):
        """Regression guard: the shared consume endpoint must not flag plain tokens."""
        magic = MagicLoginToken.create_for_user(test_user)  # requires_password_reset defaults False
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200

        test_user.refresh_from_db()
        assert test_user.needs_password_reset is False
        assert test_user.has_usable_password() is True
