"""Tests for Django settings email backend configuration."""

import pytest


@pytest.mark.unit
class TestEmailBackendConfig:
    def test_email_backend_falls_back_to_console_when_no_smtp_host(self, monkeypatch):
        """In production without EMAIL_HOST, email backend should be console (not SMTP)."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.delenv("EMAIL_HOST", raising=False)

        # Re-import settings to pick up env changes
        import importlib

        import config.settings as settings_module

        importlib.reload(settings_module)

        assert settings_module.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"


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
