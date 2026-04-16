import uuid

from django.db import models


class NotificationType(models.TextChoices):
    EVENT_INVITE = "event_invite", "Event Invite"
    EVENT_CANCELLED = "event_cancelled", "Event Cancelled"
    JOIN_REQUEST = "join_request", "Join Request"
    COHOST_ADDED = "cohost_added", "Co-host Added"
    MAGIC_LINK_REQUEST = "magic_link_request", "Magic Link Request"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.EVENT_INVITE,
    )
    event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    related_user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="related_notifications",
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} for {self.recipient}"
