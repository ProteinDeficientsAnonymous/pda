"""Refresh cookies must die when the account is paused, archived, logged out, or reset."""

import pytest
from community._validation import Code
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users._refresh_cookie import REFRESH_COOKIE_NAME
from users.models import MagicLoginToken

from tests._asserts import assert_error_code

_NEW_PASSWORD = "abcd1234ABCD!"


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    from django.core.cache import caches

    caches["ratelimit"].clear()
    yield
    caches["ratelimit"].clear()


def _login(api_client) -> str:
    response = api_client.post(
        "/api/auth/login/",
        {"phone_number": "+12025550101", "password": "testpass123"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return response.cookies[REFRESH_COOKIE_NAME].value


def _refresh(api_client, cookie: str):
    api_client.cookies[REFRESH_COOKIE_NAME] = cookie
    return api_client.post("/api/auth/refresh/", {}, content_type="application/json")


def _assert_refresh_rejected(response) -> None:
    assert response.status_code == 401
    assert_error_code(response, Code.Auth.REFRESH_TOKEN_INVALID)
    cleared = response.cookies.get(REFRESH_COOKIE_NAME)
    assert cleared is not None
    assert cleared.value == ""


@pytest.mark.django_db
class TestRefreshSession:
    def test_refresh_token_after_pause_returns_401(self, api_client, test_user):
        cookie = _login(api_client)
        test_user.is_paused = True
        test_user.save(update_fields=["is_paused"])

        _assert_refresh_rejected(_refresh(api_client, cookie))

    def test_refresh_token_after_archive_returns_401(self, api_client, test_user):
        cookie = _login(api_client)
        test_user.archived_at = timezone.now()
        test_user.save(update_fields=["archived_at"])

        _assert_refresh_rejected(_refresh(api_client, cookie))

    def test_refresh_token_after_password_invalidation_cannot_complete_onboarding(
        self, api_client, test_user
    ):
        test_user.email = "stolen@example.com"
        test_user.save(update_fields=["email"])
        cookie = _login(api_client)
        test_user.needs_password_reset = True
        test_user.set_unusable_password()
        test_user.save(update_fields=["needs_password_reset", "password"])

        refreshed = _refresh(api_client, cookie)
        _assert_refresh_rejected(refreshed)
        access = refreshed.json().get("access")
        onboard = api_client.post(
            "/api/auth/complete-onboarding/",
            {"new_password": _NEW_PASSWORD},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}" if access else "Bearer not-a-token",
        )
        assert onboard.status_code == 401
        test_user.refresh_from_db()
        assert test_user.has_usable_password() is False

    def test_refresh_token_after_logout_returns_401(self, api_client, test_user):
        cookie = _login(api_client)
        api_client.cookies[REFRESH_COOKIE_NAME] = cookie
        logged_out = api_client.post("/api/auth/logout/")
        assert logged_out.status_code == 200

        _assert_refresh_rejected(_refresh(api_client, cookie))

    def test_magic_login_session_can_complete_onboarding(self, api_client, test_user):
        test_user.email = "magic@example.com"
        test_user.save(update_fields=["email"])
        old_cookie = _login(api_client)
        magic = MagicLoginToken.create_for_user(test_user, requires_password_reset=True)
        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")
        assert response.status_code == 200, response.content

        new_cookie = response.cookies[REFRESH_COOKIE_NAME].value
        claim = RefreshToken(new_cookie).payload.get("session_version")
        test_user.refresh_from_db()
        assert claim == test_user.session_version

        refreshed = _refresh(api_client, new_cookie)
        assert refreshed.status_code == 200, refreshed.content
        onboard = api_client.post(
            "/api/auth/complete-onboarding/",
            {"new_password": _NEW_PASSWORD},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}",
        )
        assert onboard.status_code == 200, onboard.content
        test_user.refresh_from_db()
        assert test_user.check_password(_NEW_PASSWORD)
        assert test_user.needs_password_reset is False

        _assert_refresh_rejected(_refresh(api_client, old_cookie))
