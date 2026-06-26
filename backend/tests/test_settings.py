"""Tests for Django settings email backend configuration."""

import pytest


@pytest.mark.unit
class TestEmailBackendConfig:
    def test_email_backend_falls_back_to_console_when_no_smtp_host(self, monkeypatch):
        """In production without EMAIL_HOST, email backend should be console (not SMTP)."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
        # Redis is mandatory in production; set it so settings load past the
        # cache fail-fast and reach the email-backend branch under test.
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.delenv("EMAIL_HOST", raising=False)

        # Re-import settings to pick up env changes
        import importlib

        import config.settings as settings_module

        importlib.reload(settings_module)

        assert settings_module.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"


def _reload_settings():
    import importlib

    import config.settings as settings_module

    importlib.reload(settings_module)
    return settings_module


@pytest.mark.unit
class TestProductionFailFast:
    def _prod_env(self, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
        # Redis is mandatory in production; set it so these tests exercise the
        # allowed-hosts / CORS branches rather than tripping the cache check.
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    def test_allowed_hosts_empty_in_production_raises(self, monkeypatch):
        self._prod_env(monkeypatch)
        monkeypatch.setenv("ALLOWED_HOSTS", "")
        with pytest.raises(ValueError, match="ALLOWED_HOSTS"):
            _reload_settings()

    def test_allowed_hosts_filters_empty_segments(self, monkeypatch):
        self._prod_env(monkeypatch)
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com, ,foo.com,")
        settings = _reload_settings()
        assert settings.ALLOWED_HOSTS == ["example.com", "foo.com"]

    def test_cors_empty_in_production_raises(self, monkeypatch):
        self._prod_env(monkeypatch)
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
        with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS"):
            _reload_settings()

    def test_cors_allow_all_origins_disabled_in_production(self, monkeypatch):
        self._prod_env(monkeypatch)
        settings = _reload_settings()
        assert settings.CORS_ALLOW_ALL_ORIGINS is False
        assert settings.CORS_ALLOWED_ORIGINS == ["https://app.example.com"]


@pytest.mark.unit
class TestCacheConfig:
    def test_redis_url_selects_redis_backend(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        settings = _reload_settings()
        assert settings.CACHES["default"]["BACKEND"] == (
            "django.core.cache.backends.redis.RedisCache"
        )
        assert settings.CACHES["default"]["LOCATION"] == "redis://localhost:6379/0"

    def test_production_without_redis_raises(self, monkeypatch):
        # Redis is mandatory in production: the rate limiter needs a shared,
        # atomic, fixed-TTL cache. DatabaseCache (the old fallback) provides
        # none of those — its inherited incr is a non-atomic get-then-set that
        # resets the window TTL on every call — so prod must fail fast instead.
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(ValueError, match="REDIS_URL"):
            _reload_settings()

    def test_dev_without_redis_uses_locmem(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        settings = _reload_settings()
        assert settings.CACHES["default"]["BACKEND"] == (
            "django.core.cache.backends.locmem.LocMemCache"
        )
