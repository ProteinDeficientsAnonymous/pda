"""Tests for httpOnly refresh cookie + logout endpoint.

Separate file from test_auth.py because that file is already at the 500-line limit.
Covers: cookie set on login/magic-login, refresh via cookie vs body, logout clears cookie.
"""

import pytest
from ninja_jwt.tokens import RefreshToken
from users._refresh_cookie import REFRESH_COOKIE_NAME


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    # login / magic-login are rate-limited (5/m keyed on client IP); isolate counts.
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestLoginRateLimit:
    def test_login_rate_limited_after_five_attempts(self, api_client, test_user):
        from django.core.cache import cache

        cache.clear()
        for _ in range(5):
            resp = api_client.post(
                "/api/auth/login/",
                {"phone_number": "+12025550101", "password": "testpass123"},
                content_type="application/json",
            )
            assert resp.status_code == 200
        resp = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert resp.status_code == 429
        assert resp.json()["detail"][0]["code"] == "rate.limited"


@pytest.mark.django_db
class TestLoginSetsRefreshCookie:
    def test_login_sets_httponly_refresh_cookie(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        cookie = response.cookies.get(REFRESH_COOKIE_NAME)
        assert cookie is not None
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Lax"
        assert cookie["path"] == "/"
        # The refresh token lives only in the cookie now (not the JSON body).
        # Verify the cookie carries a usable refresh token.
        assert "refresh" not in response.json()
        assert RefreshToken(cookie.value) is not None

    def test_failed_login_does_not_set_cookie(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert REFRESH_COOKIE_NAME not in response.cookies


@pytest.mark.django_db
class TestMagicLoginSetsRefreshCookie:
    def test_magic_login_sets_httponly_refresh_cookie(self, api_client, test_user):
        from users.models import MagicLoginToken

        magic = MagicLoginToken.create_for_user(test_user)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200
        cookie = response.cookies.get(REFRESH_COOKIE_NAME)
        assert cookie is not None
        assert cookie["httponly"] is True
        assert "refresh" not in response.json()
        assert RefreshToken(cookie.value) is not None


@pytest.mark.django_db
class TestRefreshViaCookie:
    def test_refresh_reads_cookie_when_body_empty(self, api_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        api_client.cookies[REFRESH_COOKIE_NAME] = str(refresh)
        response = api_client.post(
            "/api/auth/refresh/",
            {},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "access" in response.json()

    def test_cookie_takes_precedence_over_body(self, api_client, test_user):
        """If both are present, the cookie wins. Matches the contract:
        the cookie is the source of truth for React; the body is Flutter-only."""
        cookie_refresh = RefreshToken.for_user(test_user)
        api_client.cookies[REFRESH_COOKIE_NAME] = str(cookie_refresh)
        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": "invalid.body.token"},
            content_type="application/json",
        )
        assert response.status_code == 200

    def test_invalid_cookie_clears_cookie(self, api_client, test_user):
        api_client.cookies[REFRESH_COOKIE_NAME] = "not.a.valid.token"
        response = api_client.post(
            "/api/auth/refresh/",
            {},
            content_type="application/json",
        )
        assert response.status_code == 401
        # Server signals the client to drop the stale cookie.
        cleared = response.cookies.get(REFRESH_COOKIE_NAME)
        assert cleared is not None
        assert cleared.value == ""

    def test_falls_back_to_body_when_no_cookie(self, api_client, test_user):
        """Flutter compat path: no cookie present, body is authoritative."""
        refresh = RefreshToken.for_user(test_user)
        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": str(refresh)},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "access" in response.json()


@pytest.mark.django_db
class TestLogout:
    def test_logout_clears_refresh_cookie(self, api_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        api_client.cookies[REFRESH_COOKIE_NAME] = str(refresh)
        response = api_client.post("/api/auth/logout/")
        assert response.status_code == 200
        cleared = response.cookies.get(REFRESH_COOKIE_NAME)
        assert cleared is not None
        assert cleared.value == ""

    def test_logout_idempotent_without_cookie(self, api_client, db):
        response = api_client.post("/api/auth/logout/")
        assert response.status_code == 200
        assert response.json()["detail"] == "logged out"
