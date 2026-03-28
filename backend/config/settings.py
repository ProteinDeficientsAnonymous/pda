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

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

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
    "config.middleware.RequestLoggingMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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

AUTH_USER_MODEL = "users.User"

DATABASES = {"default": dj_database_url.config(default="sqlite:///db.sqlite3", conn_max_age=600)}

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

if IS_PRODUCTION:
    WHITENOISE_ROOT = STATIC_ROOT / "flutter"
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
if IS_PRODUCTION:
    _cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    CORS_ALLOWED_ORIGINS = _cors_env.split(",") if _cors_env else []
else:
    CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

# Email
VETTING_EMAIL = os.environ.get("VETTING_EMAIL", "")

# WhatsApp bot
WHATSAPP_BOT_URL = os.environ.get("WHATSAPP_BOT_URL", "http://localhost:3001")
WHATSAPP_BOT_SECRET = os.environ.get("WHATSAPP_BOT_SECRET", "")
WHATSAPP_GROUP_ID = os.environ.get("WHATSAPP_GROUP_ID", "")

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
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
if IS_PRODUCTION and os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
