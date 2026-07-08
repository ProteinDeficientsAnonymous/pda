"""Tests for POST /api/auth/accept-consents/."""

import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.roles import Role


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


def _accept(api_client, user, consent_types):
    return api_client.post(
        "/api/auth/accept-consents/",
        data={"consent_types": consent_types},
        content_type="application/json",
        **_headers(user),
    )


@pytest.mark.django_db
class TestAcceptConsents:
    def test_stamps_consent_and_clears_flag(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550401", password="pass", display_name="Consenter"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])

        resp = _accept(api_client, user, ["guidelines"])
        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_guidelines_consent"] is False

        user.refresh_from_db()
        assert user.guidelines_consent_at is not None

    def test_after_consent_protected_endpoints_unblock(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550402", password="pass", display_name="Consenter"
        )
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])
        headers = _headers(user)

        # Blocked before consent.
        assert api_client.get("/api/notifications/", **headers).status_code == 403
        # Consent.
        assert _accept(api_client, user, ["guidelines"]).status_code == 200
        # Unblocked after.
        assert api_client.get("/api/notifications/", **headers).status_code == 200

    def test_already_consented_is_noop_and_preserves_timestamp(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550403", password="pass", display_name="Consenter"
        )
        first = user.guidelines_consent_at  # stamped by conftest default
        assert first is not None

        resp = _accept(api_client, user, ["guidelines"])
        assert resp.status_code == 200
        user.refresh_from_db()
        # Existing consent is never overwritten — the timestamp doesn't move.
        assert user.guidelines_consent_at == first

    def test_accepts_multiple_consent_types_together(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550405", password="pass", display_name="SmsConsenter"
        )
        user.guidelines_consent_at = None
        user.sms_consent_at = None
        user.save(update_fields=["guidelines_consent_at", "sms_consent_at"])

        resp = _accept(api_client, user, ["guidelines", "sms"])
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["needs_guidelines_consent"] is False
        assert body["needs_sms_consent"] is False

        user.refresh_from_db()
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is not None

    def test_unlisted_consent_type_is_left_null(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550406", password="pass", display_name="GuidelinesOnly"
        )
        user.guidelines_consent_at = None
        user.sms_consent_at = None
        user.save(update_fields=["guidelines_consent_at", "sms_consent_at"])

        resp = _accept(api_client, user, ["guidelines"])
        assert resp.status_code == 200, resp.content

        user.refresh_from_db()
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is None

    def test_never_overwrites_existing_consent(self, api_client):
        from django.utils import timezone
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550407", password="pass", display_name="AlreadySms"
        )
        original = timezone.now() - timezone.timedelta(days=10)
        user.guidelines_consent_at = None
        user.sms_consent_at = original
        user.save(update_fields=["guidelines_consent_at", "sms_consent_at"])

        resp = _accept(api_client, user, ["guidelines", "sms"])
        assert resp.status_code == 200, resp.content

        user.refresh_from_db()
        assert user.sms_consent_at == original

    def test_unknown_consent_type_is_rejected(self, api_client):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550408", password="pass", display_name="BadType"
        )

        resp = _accept(api_client, user, ["nonsense"])
        assert resp.status_code == 422, resp.content

    def test_requires_auth(self, api_client):
        resp = api_client.post(
            "/api/auth/accept-consents/",
            data={"consent_types": ["guidelines"]},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_admin_is_not_grandfathered(self, api_client):
        """Admins are gated too — a fresh admin with null consent is blocked."""
        admin = User.objects.create_user(
            phone_number="+12025550404", password="pass", display_name="Admin"
        )
        admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"is_default": True})
        admin.roles.add(admin_role)
        admin.guidelines_consent_at = None
        admin.save(update_fields=["guidelines_consent_at"])

        assert api_client.get("/api/notifications/", **_headers(admin)).status_code == 403
        assert _accept(api_client, admin, ["guidelines"]).status_code == 200
