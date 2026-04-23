from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone


def future_iso(days: int = 30, hours: int = 0, minutes: int = 0) -> str:
    """ISO 8601 string N days/hours/minutes ahead of now.

    Use this anywhere a test needs a valid future start/end datetime instead
    of hardcoding a year like "2026-06-01T18:00:00Z" — those strings silently
    rot as time passes and the `check_past` validator starts rejecting them.
    """
    return (timezone.now() + timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


def past_iso(days: int = 1) -> str:
    """ISO 8601 string N days in the past. Use for testing stale-draft scenarios,
    retroactive data, etc. — never for normal create/edit flows (those are rejected)."""
    return (timezone.now() - timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def use_plain_staticfiles(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def test_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550101",
        password="testpass123",
        display_name="Test Member",
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(test_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
