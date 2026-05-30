"""Tests for community endpoints: home, guidelines, check-phone, error report, FAQ."""

import json

import pytest
from users.permissions import PermissionKey
from users.roles import Role


def _pm(text: str) -> str:
    return json.dumps(
        {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manage_guidelines_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550401",
        password="guidelinespass",
        display_name="Guidelines Manager",
    )
    role = Role.objects.create(
        name="content_manager",
        permissions=[PermissionKey.EDIT_GUIDELINES],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_guidelines_headers(manage_guidelines_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_guidelines_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def edit_homepage_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550402",
        password="homepagepass",
        display_name="Homepage Editor",
    )
    role = Role.objects.create(
        name="homepage_editor",
        permissions=[PermissionKey.EDIT_HOMEPAGE],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_homepage_headers(edit_homepage_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_homepage_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def edit_faq_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550403",
        password="faqpass",
        display_name="FAQ Editor",
    )
    role = Role.objects.create(
        name="faq_editor",
        permissions=[PermissionKey.EDIT_FAQ],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_faq_headers(edit_faq_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_faq_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


# ---------------------------------------------------------------------------
# TestHomePage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHomePage:
    def test_get_home_unauthenticated(self, api_client):
        response = api_client.get("/api/community/home/")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "updated_at" in data

    def test_get_home_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/home/", **auth_headers)
        assert response.status_code == 200

    def test_update_home_content(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content_pm": _pm("New main content")},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        assert "New main content" in response.json()["content_html"]

    def test_update_home_requires_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content_pm": _pm("Blocked")},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_home_requires_auth(self, api_client):
        response = api_client.patch(
            "/api/community/home/",
            {"content_pm": _pm("No auth")},
            content_type="application/json",
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# TestGuidelines
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGuidelines:
    def test_get_guidelines_requires_auth(self, api_client):
        response = api_client.get("/api/community/guidelines/")
        assert response.status_code == 401

    def test_update_guidelines_empty_content(self, api_client, manage_guidelines_headers):
        response = api_client.patch(
            "/api/community/guidelines/",
            {"content_pm": ""},
            content_type="application/json",
            **manage_guidelines_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == ""

    def test_guidelines_has_updated_at(self, api_client, manage_guidelines_headers, auth_headers):
        api_client.patch(
            "/api/community/guidelines/",
            {"content_pm": _pm("Some content")},
            content_type="application/json",
            **manage_guidelines_headers,
        )
        response = api_client.get("/api/community/guidelines/", **auth_headers)
        assert "updated_at" in response.json()


# ---------------------------------------------------------------------------
# TestCheckPhone
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckPhone:
    def test_check_phone_exists(self, api_client, test_user):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": test_user.phone_number},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "member"

    def test_check_phone_not_exists(self, api_client, db):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": "+12025559999"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "unknown"

    def test_check_phone_invalid_format_returns_false(self, api_client, db):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": "not-a-phone"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "unknown"


# ---------------------------------------------------------------------------
# TestErrorReport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestErrorReport:
    def test_error_report_success(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {
                "error": "Something broke",
                "stack_trace": "at line 42",
                "context": "home screen",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["detail"] == "Error report received."

    def test_error_report_requires_auth(self, api_client):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "Something broke"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_error_report_minimal_fields(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "Minimal error"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201

    def test_error_report_error_too_long(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "x" * 2001},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_error_report_stack_trace_too_long(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "err", "stack_trace": "x" * 10001},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_error_report_with_enriched_fields(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {
                "error": "Something broke",
                "stack_trace": "at line 42",
                "context": "global",
                "route": "/calendar",
                "user_agent": "Mozilla/5.0",
                "app_version": "abc123",
                "client_timestamp": "2026-04-06T12:00:00Z",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["detail"] == "Error report received."


# ---------------------------------------------------------------------------
# TestFAQ
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFAQ:
    def test_get_faq_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/faq/", **auth_headers)
        assert response.status_code == 200
        assert "content" in response.json()
        assert "updated_at" in response.json()

    def test_get_faq_unauthenticated(self, api_client):
        response = api_client.get("/api/community/faq/")
        assert response.status_code == 200
        assert "content" in response.json()
        assert "updated_at" in response.json()

    def test_update_faq_content(self, api_client, edit_faq_headers):
        response = api_client.patch(
            "/api/community/faq/",
            {"content_pm": _pm("New FAQ content")},
            content_type="application/json",
            **edit_faq_headers,
        )
        assert response.status_code == 200
        assert "New FAQ content" in response.json()["content_html"]

    def test_update_faq_requires_edit_faq_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/faq/",
            {"content_pm": _pm("Should be denied")},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_faq_requires_auth(self, api_client):
        response = api_client.patch(
            "/api/community/faq/",
            {"content_pm": _pm("No auth")},
            content_type="application/json",
        )
        assert response.status_code == 401
