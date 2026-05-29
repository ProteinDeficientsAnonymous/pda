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
        assert resp.json()["detail"][0]["code"] == "email.required"

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

    def test_existing_email_user_can_skip(self, api_client, db):
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550111",
            password="x",
            display_name="Existing",
            email="existing@example.com",
            needs_onboarding=True,
        )
        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "abcd1234ABCD!"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 200, resp.content
        user.refresh_from_db()
        assert user.email == "existing@example.com"  # unchanged

    def test_complete_onboarding_clears_needs_password_reset(self, api_client, db):
        """A user forced into a reset (via self-service magic link) is cleared on submit."""
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550112",
            password="x",
            display_name="Reset Me",
            email="resetme@example.com",
        )
        user.needs_password_reset = True
        user.set_unusable_password()
        user.save(update_fields=["needs_password_reset", "password"])

        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "abcd1234ABCD!"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 200, resp.content
        user.refresh_from_db()
        assert user.needs_password_reset is False
        assert user.has_usable_password() is True
        assert resp.json()["needs_password_reset"] is False
