import pytest
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._auth import auth_headers_for

BASE = "/api/community/docs"


@pytest.fixture
def manage_docs_user(db):
    user = User.objects.create_user(
        phone_number="+15550003001",
        password="docspass123",
        first_name="Docs",
        last_name="Manager",
    )
    role = Role.objects.create(name="docs_manager", permissions=[PermissionKey.MANAGE_DOCUMENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def manage_docs_headers(manage_docs_user):
    return auth_headers_for(manage_docs_user)
