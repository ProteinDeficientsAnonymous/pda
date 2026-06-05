"""Tests for the WhatsApp status endpoint error handling/logging."""

import logging
from unittest.mock import patch

import pytest


@pytest.fixture
def whatsapp_admin_headers(db):
    from ninja_jwt.tokens import RefreshToken
    from users.models import User
    from users.permissions import PermissionKey
    from users.roles import Role

    user = User.objects.create_user(
        phone_number="+12025550909",
        password="wapass123",
        display_name="WA Admin",
    )
    role = Role.objects.create(name="wa_admin", permissions=[PermissionKey.MANAGE_WHATSAPP])
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestWhatsAppStatus:
    def test_returns_disconnected_when_no_bot_url(self, api_client, whatsapp_admin_headers):
        response = api_client.get("/api/community/whatsapp/status/", **whatsapp_admin_headers)
        assert response.status_code == 200
        assert response.json() == {"connected": False}

    def test_logs_and_returns_disconnected_on_failure(
        self, api_client, whatsapp_admin_headers, settings, caplog
    ):
        settings.WHATSAPP_BOT_URL = "https://bot.example.com"
        # The "pda" logger is configured with propagate=False, so caplog's
        # root handler never sees it. Attach caplog's capture handler directly
        # to the "pda.community" logger for the duration of the call.
        community_logger = logging.getLogger("pda.community")
        community_logger.addHandler(caplog.handler)
        original_level = community_logger.level
        community_logger.setLevel(logging.WARNING)
        try:
            with patch(
                "urllib.request.urlopen",
                side_effect=OSError("connection refused"),
            ):
                response = api_client.get(
                    "/api/community/whatsapp/status/", **whatsapp_admin_headers
                )
        finally:
            community_logger.removeHandler(caplog.handler)
            community_logger.setLevel(original_level)
        assert response.status_code == 200
        assert response.json() == {"connected": False}
        log_text = "\n".join(r.getMessage() for r in caplog.records)
        assert "whatsapp status check failed" in log_text

    def test_non_object_json_body_returns_disconnected(
        self, api_client, whatsapp_admin_headers, settings
    ):
        """Valid-but-non-object JSON must not 500 (data.get would raise AttributeError)."""
        settings.WHATSAPP_BOT_URL = "https://bot.example.com"

        class _FakeResp:
            def read(self):
                return b"[1, 2, 3]"  # valid JSON, but a list, not an object

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("urllib.request.urlopen", return_value=_FakeResp()):
            response = api_client.get("/api/community/whatsapp/status/", **whatsapp_admin_headers)

        assert response.status_code == 200
        assert response.json() == {"connected": False}

    def test_requires_permission(self, api_client, auth_headers):
        response = api_client.get("/api/community/whatsapp/status/", **auth_headers)
        assert response.status_code == 403
