"""Tests for the magic-login consume endpoint (GET /api/auth/magic-login/{token}/)."""

from datetime import timedelta

import pytest
from community.validation import Code
from django.core.cache import caches
from django.utils import timezone
from users.models import MagicLoginToken, User

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for


@pytest.mark.django_db
class TestMagicLogin:
    def test_magic_login_valid_returns_tokens(self, api_client, test_user):
        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" not in data

    def test_magic_login_sets_last_login(self, api_client, test_user):
        assert test_user.last_login is None
        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.last_login is not None

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
        test_user.save(update_fields=test_user.apply_guidelines_pause(by=None))
        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_GUIDELINES_PAUSED)

    def test_magic_login_marks_token_used(self, api_client, test_user):
        magic = MagicLoginToken.create_for_user(test_user)
        api_client.get(f"/api/auth/magic-login/{magic.token}/")
        magic.refresh_from_db()
        assert magic.used is True

    def test_magic_login_cross_user_blocked(self, api_client, test_user):
        """A logged-in user clicking another user's magic link must be rejected."""
        other = User.objects.create_user(
            phone_number="+12025550202", password="otherpass123", first_name="other"
        )
        magic = MagicLoginToken.create_for_user(other)
        headers = auth_headers_for(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/", **headers)
        assert response.status_code == 403
        magic.refresh_from_db()
        assert magic.used is False

    def test_magic_login_same_user_still_works_when_authed(self, api_client, test_user):
        """Clicking your own magic link while already logged in is allowed."""
        magic = MagicLoginToken.create_for_user(test_user)
        headers = auth_headers_for(test_user)
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

    def test_replay_after_consume_is_rejected(self, api_client, test_user):
        """A second consume of an already-consumed token must fail (TOCTOU replay
        guard: fetch + used-check + mark-used run atomically under a row lock)."""

        magic = MagicLoginToken.create_for_user(test_user)
        first = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert first.status_code == 200
        second = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert second.status_code == 400
        assert_error_code(second, Code.Auth.MAGIC_LINK_ALREADY_USED)

    def test_magic_login_rate_limited(self, api_client, test_user):

        caches["ratelimit"].clear()
        # First 5 calls pass the limiter (invalid tokens → 400, but not 429).
        for _ in range(5):
            resp = api_client.get("/api/auth/magic-login/00000000-0000-0000-0000-000000000000/")
            assert resp.status_code == 400
        resp = api_client.get("/api/auth/magic-login/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 429
        assert resp.json()["detail"][0]["code"] == "rate.limited"

    def test_rate_limit_survives_spoofed_xff(self, api_client):

        caches["ratelimit"].clear()
        url = "/api/auth/magic-login/00000000-0000-0000-0000-000000000000/"
        # Spoofed leftmost hop and the Railway proxy hop both rotate per request;
        # the limiter must still bucket on the client and trip at the 6th attempt.
        for i in range(5):
            xff = f"9.9.9.{i}, 198.51.100.7, 100.64.0.{i + 1}"
            resp = api_client.get(url, HTTP_X_FORWARDED_FOR=xff)
            assert resp.status_code == 400
        resp = api_client.get(url, HTTP_X_FORWARDED_FOR="123.45.67.89, 198.51.100.7, 100.64.0.9")
        assert resp.status_code == 429
        assert resp.json()["detail"][0]["code"] == "rate.limited"
