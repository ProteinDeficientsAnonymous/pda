import uuid
from typing import TYPE_CHECKING

from django.db import models

from users.permissions import PermissionKey

if TYPE_CHECKING:
    from django.db.models import Manager

    from users.models import User

PROTECTED_ROLE_NAMES = ("admin", "member")


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    is_default = models.BooleanField(default=False)
    permissions = models.JSONField(default=list)
    if TYPE_CHECKING:
        users: "Manager[User]"

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_default_admin(self) -> bool:
        return self.name == "admin" and self.is_default

    @property
    def effective_permissions(self) -> list[str]:
        """Permission keys this role grants: all keys for the default admin role, else the stored keys coerced to a clean list[str] (legacy/corrupt rows may hold non-list or non-string values)."""
        if self.is_default_admin:
            return list(PermissionKey.values)
        stored = self.permissions
        if not isinstance(stored, list):
            return []
        return [p for p in stored if isinstance(p, str)]

    @classmethod
    def ids_with_permission(cls, permission: str) -> list[str]:
        """Ids of roles granting ``permission``, honoring the admin-default rule.

        Resolved in Python via ``effective_permissions`` rather than a
        ``permissions__contains`` JSONField lookup, which is unsupported on
        SQLite. Callers filter users with ``roles__id__in`` for a portable query.
        """
        return [str(r.id) for r in cls.objects.all() if permission in r.effective_permissions]

    @classmethod
    def ids_granting_explicitly(cls, permission: str) -> list[str]:
        """Like ids_with_permission, but the default admin role doesn't count."""
        return [
            str(r.id)
            for r in cls.objects.all()
            if not r.is_default_admin and permission in r.effective_permissions
        ]
