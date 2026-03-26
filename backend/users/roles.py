import uuid
from typing import TYPE_CHECKING

from django.db import models

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
