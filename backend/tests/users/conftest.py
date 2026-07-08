import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_users_user(db):
    user = User.objects.create_user(
        phone_number="+12025550201",
        password="managerpass123",
        display_name="User Manager",
    )
    role = Role.objects.create(
        name="user_manager",
        permissions=[PermissionKey.MANAGE_USERS, PermissionKey.CREATE_USER],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_users_headers(manage_users_user):
    refresh = RefreshToken.for_user(manage_users_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550301",
        password="otherpass123",
        display_name="Other User",
    )


@pytest.fixture
def member(db):
    """A member User (is_member=True). Reusable across user test files."""
    return User.objects.create_user(
        phone_number="+12025550401",
        password="memberpass123",
        display_name="Member User",
    )


@pytest.fixture
def non_member(db):
    """A non-member User (is_member=False) — e.g. a public-RSVP account.

    Passes is_member=False explicitly to override the conftest create_user
    monkeypatch, which otherwise forces is_member=True for the test population.
    """
    return User.objects.create_user(
        phone_number="+12025550402",
        display_name="Non-member User",
        is_member=False,
    )
