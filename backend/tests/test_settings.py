"""Tests for Django settings email backend configuration."""

import warnings

import pytest
from django.conf import settings as dj_settings
from django.core import mail
from django.utils.deprecation import RemovedInDjango70Warning


@pytest.mark.unit
class TestEmailBackendConfig:
    def test_email_backend_falls_back_to_console_when_no_smtp_host(
        self, monkeypatch, reload_settings
    ):
        """In production without EMAIL_HOST, email backend should be console (not SMTP)."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.delenv("EMAIL_HOST", raising=False)

        with warnings.catch_warnings():
            warnings.simplefilter("error", RemovedInDjango70Warning)
            settings_module = reload_settings()

        assert (
            settings_module.MAILERS["default"]["BACKEND"]
            == "django.core.mail.backends.console.EmailBackend"
        )

    def test_email_backend_uses_smtp_when_host_set(self, monkeypatch, reload_settings):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("EMAIL_HOST", "smtp.example.com")
        monkeypatch.setenv("EMAIL_HOST_USER", "user")
        monkeypatch.setenv("EMAIL_HOST_PASSWORD", "secret")
        monkeypatch.setenv("DEFAULT_FROM_EMAIL", "pda@example.com")

        # The test runner stores a locmem mailer on Django's settings object.
        # Reloading the module does not replace that, so publish the reloaded
        # config before asking Django to build a connection.
        previous_mailers = dj_settings.MAILERS
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RemovedInDjango70Warning)
                settings_module = reload_settings()
                dj_settings.MAILERS = settings_module.MAILERS
                connection = mail.mailers["default"]
        finally:
            dj_settings.MAILERS = previous_mailers
        mailer = settings_module.MAILERS["default"]

        assert mailer["BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
        assert connection.host == "smtp.example.com"
        assert connection.port == 587
        assert connection.username == "user"
        assert connection.password == "secret"
        assert connection.use_tls is True
        assert settings_module.DEFAULT_FROM_EMAIL == "pda@example.com"


@pytest.fixture
def reload_settings(monkeypatch):
    import importlib

    import config.settings as settings_module

    yield lambda: importlib.reload(settings_module)
    monkeypatch.undo()
    importlib.reload(settings_module)


@pytest.mark.unit
class TestDatabaseConfig:
    def test_postgres_uses_connection_pool(self, monkeypatch, reload_settings):
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/pda")
        monkeypatch.delenv("PDA_DB_POOL_MAX_SIZE", raising=False)

        db = reload_settings().DATABASES["default"]

        assert db["OPTIONS"]["pool"] == {"min_size": 2, "max_size": 10}
        assert db["CONN_MAX_AGE"] == 0

    def test_pool_max_size_reads_env(self, monkeypatch, reload_settings):
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/pda")
        monkeypatch.setenv("PDA_DB_POOL_MAX_SIZE", "4")

        db = reload_settings().DATABASES["default"]

        assert db["OPTIONS"]["pool"]["max_size"] == 4

    def test_sqlite_has_no_pool(self, monkeypatch, reload_settings):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///dev.db")

        db = reload_settings().DATABASES["default"]

        assert "pool" not in db.get("OPTIONS", {})
