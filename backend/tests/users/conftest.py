import pytest
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_users_user(db):
    from users.models import User

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
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_users_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def other_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550301",
        password="otherpass123",
        display_name="Other User",
    )
