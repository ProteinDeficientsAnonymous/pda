from itertools import count

from django.utils import timezone
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


def make_attendance_paused(**fields) -> User:
    return make_user(is_member=False, attendance_paused_at=timezone.now(), **fields)


def grant(user: User, *permissions: PermissionKey) -> Role:
    role = Role.objects.create(name=f"test-role-{next(_roles)}", permissions=list(permissions))
    user.roles.add(role)
    return role
