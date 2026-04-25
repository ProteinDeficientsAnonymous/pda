"""EventCoHostInvite model — invite/accept/decline flow for event co-hosts."""

import uuid
from typing import TYPE_CHECKING

from django.db import models

from community.models.choices import CoHostInviteStatus


class EventCoHostInvite(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        user_id: uuid.UUID
        invited_by_id: uuid.UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "community.Event",
        on_delete=models.CASCADE,
        related_name="cohost_invites",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="cohost_invites_received",
    )
    invited_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cohost_invites_sent",
    )
    status = models.CharField(
        max_length=20,
        choices=CoHostInviteStatus.choices,
        default=CoHostInviteStatus.PENDING,
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "community"
        ordering = ["-invited_at"]
        constraints = [
            models.UniqueConstraint(fields=("event", "user"), name="unique_event_cohost_invite"),
        ]

    def __str__(self):
        return f"{self.user} → {self.event.title} ({self.status})"
