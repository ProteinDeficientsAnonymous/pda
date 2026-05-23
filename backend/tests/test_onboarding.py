"""Tests for complete-onboarding email requirement (Task 4.1)."""

import pytest


@pytest.mark.django_db
class TestOnboardingEmail:
    def test_missing_email_rejected(self, api_client, needs_onboarding_auth_headers):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "abcd1234ABCD!", "display_name": "Newby"},
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 422

    def test_malformed_email_rejected(self, api_client, needs_onboarding_auth_headers):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "not-an-email",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 422

    def test_email_required_and_lowercased(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "Newby@Example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.email == "newby@example.com"

    def test_duplicate_email_rejected(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="other", email="taken@example.com"
        )
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "Taken@Example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"
