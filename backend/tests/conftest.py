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
    from users.permissions import PermissionKey
    from users.roles import Role

    user = User.objects.create_user(
        phone_number="+12025550101",
        password="testpass123",
        display_name="Test Member",
    )
    role = Role.objects.create(
        name="test_member_role",
        permissions=[PermissionKey.MANAGE_EVENTS],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def auth_headers(test_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(test_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
