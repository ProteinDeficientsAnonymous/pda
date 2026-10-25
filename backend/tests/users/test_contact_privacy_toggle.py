import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}  # type: ignore


@pytest.mark.django_db
class TestContactPrivacyToggleStampsConsent:
    def test_reshowing_phone_from_settings_does_not_trigger_consent_gate(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550911",
            password="pass",
            first_name="Toggler",
            last_name="",
            show_phone=False,
        )
        assert user.contact_privacy_consent_at is None

        resp = api_client.patch(
            "/api/auth/me/",
            {"show_phone": True},
            content_type="application/json",
            **_headers(user),
        )

        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_contact_privacy_consent"] is False
        user.refresh_from_db()
        assert user.contact_privacy_consent_at is not None

    def test_unrelated_patch_does_not_stamp_contact_privacy(self, api_client):
        user = User.objects.create_user(
            phone_number="+12025550912", password="pass", first_name="Other", last_name=""
        )

        resp = api_client.patch(
            "/api/auth/me/",
            {"pronouns": "they/them"},
            content_type="application/json",
            **_headers(user),
        )

        assert resp.status_code == 200, resp.content
        user.refresh_from_db()
        assert user.contact_privacy_consent_at is None
