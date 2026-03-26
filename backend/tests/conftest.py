import pytest
from django.test import Client


@pytest.fixture(autouse=True)
def use_plain_staticfiles(settings):
    settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def test_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+15550001001",
        password="testpass123",
        display_name="Test Member",
    )


@pytest.fixture
def auth_headers(test_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(test_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
