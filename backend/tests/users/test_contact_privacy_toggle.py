from datetime import timedelta

import pytest
from django.utils import timezone
from users import _auth

ME_URL = "/api/auth/me/"


@pytest.fixture
def audit_events(monkeypatch):
    events: list[str] = []
    monkeypatch.setattr(_auth, "audit_log", lambda _level, event, *a, **kw: events.append(event))
    return events


@pytest.mark.django_db
class TestContactPrivacyToggleStampsConsent:
    @pytest.mark.parametrize(
        "case",
        [
            ("show_phone", {"show_phone": True}),
            ("show_email", {"show_email": True}),
            ("show_phone", {"show_email": False}),
        ],
    )
    def test_contact_toggle_stamps_consent(
        self, api_client, test_user, auth_headers, audit_events, case
    ):
        hidden_field, patch = case
        setattr(test_user, hidden_field, False)
        test_user.save(update_fields=[hidden_field])

        resp = api_client.patch(ME_URL, patch, content_type="application/json", **auth_headers)

        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_contact_privacy_consent"] is False
        test_user.refresh_from_db()
        assert test_user.contact_privacy_consent_at is not None
        assert "consents_accepted" in audit_events

    def test_toggle_keeps_existing_consent_timestamp(
        self, api_client, test_user, auth_headers, audit_events
    ):
        earlier = timezone.now() - timedelta(days=30)
        test_user.contact_privacy_consent_at = earlier
        test_user.save(update_fields=["contact_privacy_consent_at"])

        resp = api_client.patch(
            ME_URL, {"show_phone": False}, content_type="application/json", **auth_headers
        )

        assert resp.status_code == 200, resp.content
        test_user.refresh_from_db()
        assert test_user.contact_privacy_consent_at == earlier
        assert "consents_accepted" not in audit_events

    def test_unrelated_patch_does_not_stamp_contact_privacy(
        self, api_client, test_user, auth_headers, audit_events
    ):
        resp = api_client.patch(
            ME_URL, {"pronouns": "they/them"}, content_type="application/json", **auth_headers
        )

        assert resp.status_code == 200, resp.content
        test_user.refresh_from_db()
        assert test_user.contact_privacy_consent_at is None
        assert "consents_accepted" not in audit_events
