from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from community.models import JoinFormQuestion, JoinRequest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.test import Client
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from notifications import email_sender as email_sender_module
from notifications.email_sender import SendResult
from users.models import User, UserManager
from users.permissions import PermissionKey
from users.roles import Role


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


def pytest_configure() -> None:
    # Fast MD5 hasher for tests only — default PBKDF2 is ~600k iterations per create_user.
    django_settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


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
def why_join_id(db):
    q = JoinFormQuestion.objects.filter(required=True).first()
    return str(q.id) if q else ""


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _default_test_users_consented(monkeypatch):
    """Make test-created users count as already-consented to the guidelines.

    The hard guidelines-consent gate (config.auth.GatedJWTAuth) 403s any user
    whose guidelines_consent_at is null, which is the correct production default
    (nobody is grandfathered — see User.guidelines_consent_at). But the vast
    majority of tests create a plain member via create_user and then exercise an
    unrelated gated endpoint; without this they'd all 403. Stamp consent on
    create so the default test user behaves like a normal, set-up member.

    Tests that specifically exercise the consent gate explicitly set
    guidelines_consent_at = None on their user to opt back into the gated state.
    """
    original = UserManager.create_user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("guidelines_consent_at", timezone.now())
        extra_fields.setdefault("is_member", True)
        return original(self, phone_number, password=password, **extra_fields)

    monkeypatch.setattr(UserManager, "create_user", create_user)


@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        phone_number="+12025550101",
        password="testpass123",
        first_name="Test",
        last_name="Member",
    )
    return user


@pytest.fixture
def auth_headers(test_user):
    refresh = RefreshToken.for_user(test_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def vettor_user(db):
    user = User.objects.create_user(
        phone_number="+12025550003",
        password="vettorpass123",
        first_name="Vettor",
    )
    role = Role.objects.create(name="vettor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
    user.roles.add(role)
    return user


@pytest.fixture
def vettor_headers(vettor_user):
    refresh = RefreshToken.for_user(vettor_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_users_user(db):
    user = User.objects.create_user(
        phone_number="+12025550010",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )
    role = Role.objects.create(
        name="admin_mgr",
        permissions=[PermissionKey.MANAGE_USERS, PermissionKey.CREATE_USER],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_users_headers(manage_users_user):
    refresh = RefreshToken.for_user(manage_users_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_roles_user(db):
    user = User.objects.create_user(
        phone_number="+12025550011",
        password="rolemgrpass123",
        first_name="Role",
        last_name="Manager",
    )
    role = Role.objects.create(
        name="role_mgr",
        permissions=[PermissionKey.MANAGE_USERS, PermissionKey.MANAGE_ROLES],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_roles_headers(manage_roles_user):
    refresh = RefreshToken.for_user(manage_roles_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def needs_onboarding_user(db):
    return User.objects.create_user(
        phone_number="+12025550110",
        password="x",
        first_name="",
        needs_onboarding=True,
    )


@pytest.fixture
def needs_onboarding_auth_headers(needs_onboarding_user):
    refresh = RefreshToken.for_user(needs_onboarding_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def sample_join_request(db):
    q = JoinFormQuestion.objects.filter(required=True).first()
    answers = {}
    if q:
        answers[str(q.id)] = {"label": q.label, "answer": "I believe in collective liberation."}
    return JoinRequest.objects.create(
        first_name="Sprout",
        last_name="Seedling",
        phone_number="+16505551234",
        custom_answers=answers,
    )


@pytest.fixture
def fake_email_sender(monkeypatch):
    """Replace the cached email sender with a Mock so integration tests can assert sends.

    Yields the Mock so tests can inspect call args and tweak return values.
    """
    fake = MagicMock()
    fake.send.return_value = SendResult(success=True, provider_message_id="test_msg")

    # Set the module-level cache directly. get_email_sender() returns
    # whatever is in _cached_sender if it's not None.
    monkeypatch.setattr(email_sender_module, "_cached_sender", fake)
    yield fake
    # monkeypatch auto-cleans up.
