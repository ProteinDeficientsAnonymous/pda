"""Tests for complete-onboarding email requirement (Task 4.1)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User


@pytest.mark.django_db
class TestOnboardingEmail:
    def test_missing_email_rejected(self, api_client, needs_onboarding_auth_headers):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "abcd1234ABCD!", "first_name": "Newby"},
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
                "first_name": "Newby",
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
                "first_name": "Newby",
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
        User.objects.create_user(
            phone_number="+12025550199", first_name="other", email="taken@example.com"
        )
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "first_name": "Newby",
                "email": "Taken@Example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"

    def test_existing_email_user_can_skip(self, api_client, db):
        user = User.objects.create_user(
            phone_number="+12025550111",
            password="x",
            first_name="Existing",
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
        user = User.objects.create_user(
            phone_number="+12025550112",
            password="x",
            first_name="Reset",
            last_name="Me",
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

    def test_complete_onboarding_rejects_reusing_usable_password(self, api_client, db):
        """A user who still has a usable password can't 'reset' to the same one."""
        user = User.objects.create_user(
            phone_number="+12025550113",
            password="SamePass123!",
            first_name="Reuser",
            email="reuser@example.com",
        )
        user.needs_password_reset = True  # has a usable password AND a pending reset
        user.save(update_fields=["needs_password_reset"])
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "SamePass123!"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"][0]["code"] == "password.same_as_old"

    def test_complete_onboarding_reset_user_can_set_any_password(self, api_client, db):
        """A forced-reset user has an unusable password, so the reuse check must NOT
        false-positive and block them from setting a password."""
        user = User.objects.create_user(
            phone_number="+12025550114",
            password="x",
            first_name="Fresh",
            last_name="Start",
            email="fresh@example.com",
        )
        user.needs_password_reset = True
        user.set_unusable_password()
        user.save(update_fields=["needs_password_reset", "password"])
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "AnyNewPass123!"},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 200, resp.content


@pytest.mark.django_db
class TestSmsConsentSerialized:
    def test_me_reports_needs_sms_consent_when_null(self, api_client, needs_onboarding_user):
        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(update_fields=["sms_consent_at"])
        token = RefreshToken.for_user(needs_onboarding_user).access_token
        resp = api_client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_sms_consent"] is True


@pytest.mark.django_db
class TestOnboardingConsent:
    def test_accept_flags_stamp_both_consents(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        needs_onboarding_user.guidelines_consent_at = None
        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(update_fields=["guidelines_consent_at", "sms_consent_at"])
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "first_name": "Newby",
                "email": "newby@example.com",
                "consent_types": ["guidelines", "sms"],
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["needs_guidelines_consent"] is False
        assert body["needs_sms_consent"] is False
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.guidelines_consent_at is not None
        assert needs_onboarding_user.sms_consent_at is not None

    def test_omitted_flags_leave_consents_untouched(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        needs_onboarding_user.guidelines_consent_at = None
        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(update_fields=["guidelines_consent_at", "sms_consent_at"])
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "first_name": "Newby",
                "email": "newby@example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.guidelines_consent_at is None
        assert needs_onboarding_user.sms_consent_at is None

    def test_accept_does_not_overwrite_existing_consent(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        earlier = timezone.now() - timedelta(days=30)
        needs_onboarding_user.guidelines_consent_at = earlier
        needs_onboarding_user.save(update_fields=["guidelines_consent_at"])
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "first_name": "Newby",
                "email": "newby@example.com",
                "consent_types": ["guidelines"],
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.guidelines_consent_at == earlier
