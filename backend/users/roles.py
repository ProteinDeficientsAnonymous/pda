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
    def effective_permissions(self) -> list[str]:
        """Admin role implicitly grants every permission (see User.has_permission).
        Return the current PermissionKey set so the UI reflects reality even if
        the DB row was seeded before newer keys were added.

        Coerces the JSONField to a clean list[str] (corrupt/out-of-band rows may
        hold non-list/non-string values) so RoleOut.permissions holds for every consumer.
        """
        if self.name == "admin" and self.is_default:
            return list(PermissionKey.values)
        raw = self.permissions
        if not isinstance(raw, list):
            return []
        return [p for p in raw if isinstance(p, str)]
