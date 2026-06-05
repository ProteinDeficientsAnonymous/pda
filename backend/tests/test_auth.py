"""Tests for auth endpoints: login, refresh, me, change-password, onboarding."""

import pytest
from community._validation import Code
from ninja_jwt.tokens import RefreshToken

from tests._asserts import assert_error_code

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# Rate-limit cache isolation is handled by the package-wide autouse
# `_clear_rate_limit_cache` fixture in conftest.py.


@pytest.fixture
def onboarding_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550901",
        password="temppass123",
        display_name="",
        needs_onboarding=True,
    )


@pytest.fixture
def onboarding_headers(onboarding_user):
    refresh = RefreshToken.for_user(onboarding_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


# ---------------------------------------------------------------------------
# TestLogin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLogin:
    def test_login_valid_returns_tokens(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        # The refresh token is delivered via the httpOnly cookie only — never
        # in the JSON body (would expose it to JS / XSS theft for no benefit).
        assert "refresh" not in data

    def test_login_wrong_password(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert_error_code(response, Code.Auth.INVALID_CREDENTIALS)

    def test_login_unknown_phone(self, api_client, db):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025559900", "password": "anypassword"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_missing_password(self, api_client, db):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_login_missing_phone(self, api_client, db):
        response = api_client.post(
            "/api/auth/login/",
            {"password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_login_email_format_rejected(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_paused_user_returns_403(self, api_client, test_user):
        test_user.is_paused = True
        test_user.save(update_fields=["is_paused"])
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_PAUSED)


# ---------------------------------------------------------------------------
# TestRefreshToken
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRefreshToken:
    def test_refresh_valid_returns_new_access(self, api_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": str(refresh)},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert "access" in response.json()

    def test_refresh_invalid_token(self, api_client, db):
        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": "not.a.valid.token"},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert_error_code(response, Code.Auth.REFRESH_TOKEN_INVALID)

    def test_refresh_missing_field(self, api_client, db):
        # With httpOnly cookie support, the body field is optional: the token
        # may come from the `refresh_token` cookie instead. Missing both surfaces
        # as a 401, not a 422 — since "no token available" is an auth failure,
        # not a payload shape failure.
        response = api_client.post(
            "/api/auth/refresh/",
            {},
            content_type="application/json",
        )
        assert response.status_code == 401
        assert_error_code(response, Code.Auth.REFRESH_TOKEN_INVALID)

    def test_refresh_empty_string(self, api_client, db):
        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": ""},
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestMe
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMe:
    def test_me_returns_user_fields(self, api_client, auth_headers, test_user):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == test_user.phone_number
        assert data["display_name"] == "Test Member"
        assert data["week_start"] == "sunday"
        assert "roles" in data
        assert isinstance(data["roles"], list)

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_me_invalid_token(self, api_client):
        response = api_client.get("/api/auth/me/", HTTP_AUTHORIZATION="Bearer invalid.token.here")
        assert response.status_code == 401

    def test_me_returns_needs_onboarding_flag(self, api_client, onboarding_headers):
        response = api_client.get("/api/auth/me/", **onboarding_headers)
        assert response.status_code == 200
        assert response.json()["needs_onboarding"] is True

    def test_me_paused_user_returns_403(self, api_client, test_user):
        from ninja_jwt.tokens import RefreshToken

        test_user.is_paused = True
        test_user.save(update_fields=["is_paused"])
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(test_user).access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Auth.ACCOUNT_PAUSED)


# ---------------------------------------------------------------------------
# TestChangePassword
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, api_client, auth_headers, test_user):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "NewPassword456!"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Password updated successfully."
        test_user.refresh_from_db()
        assert test_user.check_password("NewPassword456!")

    def test_change_password_wrong_current(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "wrongpass", "new_password": "NewPassword456!"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Auth.CURRENT_PASSWORD_INCORRECT)

    def test_change_password_rejects_reuse(self, api_client, db):
        """New password must differ from the current one."""
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550401", password="ReusedPass123!", display_name="Reuse"
        )
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "ReusedPass123!", "new_password": "ReusedPass123!"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Password.SAME_AS_OLD, "new_password")

    def test_change_password_clears_needs_password_reset(self, api_client, db):
        """Setting a password via change-password satisfies a pending forced reset."""
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550402", password="OldPass123!", display_name="Pending"
        )
        user.needs_password_reset = True
        user.save(update_fields=["needs_password_reset"])
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "OldPass123!", "new_password": "BrandNew456!"},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.needs_password_reset is False

    def test_change_password_too_short(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "short"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("12 characters" in r for r in match["params"]["reasons"])

    def test_change_password_missing_uppercase(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "nouppercase123!"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("uppercase" in r for r in match["params"]["reasons"])

    def test_change_password_missing_number(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "NoNumberHere!!!"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("number" in r for r in match["params"]["reasons"])

    def test_change_password_missing_special_char(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "NoSpecialChar1X"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("special" in r for r in match["params"]["reasons"])

    def test_change_password_multiple_failures(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "short"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        reasons = match["params"]["reasons"]
        assert any("12 characters" in r for r in reasons)
        assert any("uppercase" in r for r in reasons)
        assert any("number" in r for r in reasons)
        assert any("special" in r for r in reasons)

    def test_change_password_requires_auth(self, api_client):
        response = api_client.post(
            "/api/auth/change-password/",
            {"current_password": "testpass123", "new_password": "NewPassword456!"},
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestCompleteOnboarding
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompleteOnboarding:
    def test_complete_onboarding_success(self, api_client, onboarding_headers, onboarding_user):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {
                "display_name": "New Name",
                "new_password": "SecurePass99!",
                "email": "newname@example.com",
            },
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "New Name"
        assert data["needs_onboarding"] is False
        onboarding_user.refresh_from_db()
        assert onboarding_user.needs_onboarding is False
        assert onboarding_user.onboarded_at is not None
        assert onboarding_user.check_password("SecurePass99!")

    def test_complete_onboarding_with_email(self, api_client, onboarding_headers, onboarding_user):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "SecurePass99!", "email": "user@example.com"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 200
        onboarding_user.refresh_from_db()
        assert onboarding_user.email == "user@example.com"

    def test_complete_onboarding_password_too_short(self, api_client, onboarding_headers):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "short"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("12 characters" in r for r in match["params"]["reasons"])

    def test_complete_onboarding_missing_uppercase(self, api_client, onboarding_headers):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "nouppercase123!"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("uppercase" in r for r in match["params"]["reasons"])

    def test_complete_onboarding_missing_number(self, api_client, onboarding_headers):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "NoNumberHere!!!"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("number" in r for r in match["params"]["reasons"])

    def test_complete_onboarding_missing_special_char(self, api_client, onboarding_headers):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "NoSpecialChar1X"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 400
        match = assert_error_code(response, Code.Password.INVALID, "new_password")
        assert any("special" in r for r in match["params"]["reasons"])

    def test_complete_onboarding_requires_auth(self, api_client):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "SecurePass99!"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_complete_onboarding_strips_display_name_whitespace(
        self, api_client, onboarding_headers, onboarding_user
    ):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {
                "display_name": "  Padded Name  ",
                "new_password": "SecurePass99!",
                "email": "padded@example.com",
            },
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Padded Name"

    def test_complete_onboarding_invalid_email_rejected(self, api_client, onboarding_headers):
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "SecurePass99!", "email": "notanemail"},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 422

    def test_complete_onboarding_empty_email_rejected(self, api_client, onboarding_headers):
        # email is now required; empty string is invalid
        response = api_client.post(
            "/api/auth/complete-onboarding/",
            {"display_name": "Named", "new_password": "SecurePass99!", "email": ""},
            content_type="application/json",
            **onboarding_headers,
        )
        assert response.status_code == 422
