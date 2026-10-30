from itertools import count

from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

_phones = count(1)
_roles = count(1)


def make_user(*permissions: PermissionKey, **fields) -> User:
    """fields(dict): create_user kwargs; phone_number, email, password, first_name get defaults."""
    phone = fields.setdefault("phone_number", f"+1312555{next(_phones):04d}")
    fields.setdefault("email", f"{phone}@example.test")
    fields.setdefault("password", "Testpass123!")
    fields.setdefault("first_name", "Test")
    user = User.objects.create_user(**fields)
    if permissions:
        grant(user, *permissions)
    return user


def grant(user: User, *permissions: PermissionKey) -> Role:
    role = Role.objects.create(name=f"test-role-{next(_roles)}", permissions=list(permissions))
    user.roles.add(role)
    return role
