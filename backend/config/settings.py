import base64
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

IS_PRODUCTION = os.environ.get("RAILWAY_ENVIRONMENT") is not None

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ValueError("SECRET_KEY must be set in production")
    SECRET_KEY = "django-insecure-development-key-only"

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS:
    if IS_PRODUCTION:
        raise ValueError("ALLOWED_HOSTS must be set in production")
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "ninja_jwt",
    "users",
    "community",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.RequestLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "users.User"

DATABASES = {"default": dj_database_url.config(default="sqlite:///db.sqlite3", conn_max_age=600)}

# Cache — backs the cross-worker rate limiter (see config/ratelimit.py).
# A shared cache is REQUIRED for rate limiting to hold across gunicorn/uvicorn
# workers: LocMemCache is per-process, so each worker keeps its own counter and
# the effective limit is multiplied by the worker count.
#
# The rate limiter depends on `cache.incr` being atomic and `cache.add` setting
# the window TTL exactly once at first hit. Only Redis (and LocMemCache, which
# overrides incr) honor that contract. DatabaseCache inherits BaseCache.incr,
# which does a non-atomic get-then-set (the TOCTOU race this code aims to
# eliminate) and resets the row's TTL to DEFAULT_TIMEOUT on every increment —
# corrupting the window length. So we never use DatabaseCache here.
#
#   * REDIS_URL set  -> Redis (shared, atomic incr) — correct for multi-worker.
#   * else, prod     -> hard error. Redis is mandatory in production so the
#                       rate limiter is both shared and correct.
#   * else, dev/test -> LocMemCache (single process, fine locally; its incr
#                       override preserves the TTL).
_REDIS_URL = os.environ.get("REDIS_URL", "")
if _REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
        }
    }
elif IS_PRODUCTION:
    raise ValueError(
        "REDIS_URL must be set in production: the rate limiter requires a "
        "shared cache with atomic incr and a fixed-at-first-hit TTL, which only "
        "Redis provides across workers."
    )
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES: dict[str, dict[str, object]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if IS_PRODUCTION:
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }

# Backblaze B2 object storage (S3-compatible) for user-uploaded media.
# When B2_KEY_ID is set, media files go to B2 instead of local disk.
if os.environ.get("B2_KEY_ID"):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": os.environ["B2_KEY_ID"],
            "secret_key": os.environ["B2_APPLICATION_KEY"],
            "bucket_name": os.environ["B2_BUCKET_NAME"],
            "endpoint_url": os.environ["B2_ENDPOINT_URL"],
            "region_name": os.environ.get("B2_REGION", "us-west-004"),
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Number of trusted reverse proxies in front of the app. Used to derive the
# real client IP from X-Forwarded-For for rate limiting (config/ratelimit.py).
# Railway adds exactly one hop. This is ONLY sound when the app is unreachable
# except via the trusted proxy chain.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

# HTTPS / security headers
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# CORS
# Never allow all origins: CORS_ALLOW_CREDENTIALS=True below means a wildcard
# would let any site make authenticated cross-origin requests with the user's
# cookies. Keep this an explicit allowlist.
CORS_ALLOW_ALL_ORIGINS = False
if IS_PRODUCTION:
    _cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
    if not CORS_ALLOWED_ORIGINS:
        raise ValueError("CORS_ALLOWED_ORIGINS must be set in production")
else:
    CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://0.0.0.0:3000"]

# httpOnly refresh cookie is sent cross-origin in dev (React :3000 → Django :8000).
# Required so the browser includes the cookie in fetch/axios withCredentials requests.
CORS_ALLOW_CREDENTIALS = True

# Email
VETTING_EMAIL = os.environ.get("VETTING_EMAIL", "")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "config.logging_config.JsonFormatter"},
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "filters": {
        "sensitive": {"()": "config.logging_config.SensitiveDataFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if IS_PRODUCTION else "simple",
            "filters": ["sensitive"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING" if IS_PRODUCTION else "DEBUG",
    },
    "loggers": {
        "pda": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "pda.audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

GITHUB_APP_ID = os.environ.get("GITHUB_APP_ID", "")
GITHUB_APP_INSTALLATION_ID = os.environ.get("GITHUB_APP_INSTALLATION_ID", "")
_github_app_private_key_b64 = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
GITHUB_APP_PRIVATE_KEY = (
    base64.b64decode(_github_app_private_key_b64).decode() if _github_app_private_key_b64 else ""
)
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
if IS_PRODUCTION and os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "")

if IS_PRODUCTION and RESEND_API_KEY and not RESEND_FROM_EMAIL:
    raise ValueError("RESEND_FROM_EMAIL must be set when RESEND_API_KEY is configured")

# Frontend URL used to construct magic-login links in transactional emails.
# In production, set to the public app URL (e.g. https://pda.example.com).
# In dev/test, defaults to localhost:3000.
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")
