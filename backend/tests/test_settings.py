"""Tests for Django settings email backend configuration."""

import pytest


@pytest.mark.unit
class TestEmailBackendConfig:
    def test_email_backend_falls_back_to_console_when_no_smtp_host(self, monkeypatch):
        """In production without EMAIL_HOST, email backend should be console (not SMTP)."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.delenv("EMAIL_HOST", raising=False)

        # Re-import settings to pick up env changes
        import importlib

        import config.settings as settings_module

        importlib.reload(settings_module)

        assert settings_module.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"
