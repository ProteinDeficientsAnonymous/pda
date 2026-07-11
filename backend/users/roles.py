import uuid
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Q

from users.permissions import PermissionKey

if TYPE_CHECKING:
    from django.db.models import Manager

    from users.models import User

PROTECTED_ROLE_NAMES = ("admin", "member")

# Live members holding a role — excludes archived and non-member rows. Reused as a
# reverse-relation predicate (annotation filter=) and by Role.live_member_count.
LIVE_ROLE_MEMBER = Q(users__archived_at__isnull=True, users__is_member=True)


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

    def live_member_count(self) -> int:
        """Count of live members holding this role — excludes archived and non-members."""
        return self.users.filter(archived_at__isnull=True, is_member=True).count()

    @property
    def effective_permissions(self) -> list[str]:
        """Permission keys this role grants: all keys for the default admin role, else the stored keys coerced to a clean list[str] (legacy/corrupt rows may hold non-list or non-string values)."""
        if self.name == "admin" and self.is_default:
            return list(PermissionKey.values)
        stored = self.permissions
        if not isinstance(stored, list):
            return []
        return [p for p in stored if isinstance(p, str)]
