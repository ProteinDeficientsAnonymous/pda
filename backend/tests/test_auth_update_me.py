"""Tests for PATCH /api/auth/me/ (update profile)."""

import pytest


@pytest.mark.django_db
class TestUpdateMe:
    def test_update_me_invalid_email_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": "notanemail"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_update_me_valid_email_accepted(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": "valid@example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "valid@example.com"

    def test_update_me_empty_email_accepted(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"email": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200

    def test_update_week_start_to_monday(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"week_start": "monday"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["week_start"] == "monday"

    def test_update_week_start_invalid_value_rejected(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/auth/me/",
            {"week_start": "wednesday"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422
