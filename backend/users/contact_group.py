import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan


class ContactGroup(models.Model):
    """A member-owned, named set of people for batch event invites."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contact_groups",
        db_index=False,  # covered by the (owner, lower(name)) unique index
    )
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="+",  # no member→group accessor: groups are the owner's private lists
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                "owner", Lower("name"), name="unique_contact_group_name_per_owner"
            ),
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim("name")), 0),
                name="contact_group_name_not_blank",
            ),
        ]

    def save(self, *args, **kwargs):
        # str.strip() covers tabs/newlines, which the DB's TRIM check doesn't
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
