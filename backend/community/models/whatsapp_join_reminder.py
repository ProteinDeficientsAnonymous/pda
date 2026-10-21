import uuid

from django.db import models


class WhatsAppJoinReminder(models.Model):
    """One row per reminder sent, so a run can tell who is already caught up."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="whatsapp_join_reminders"
    )
    reminder_number = models.PositiveSmallIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "reminder_number"],
                name="unique_whatsapp_join_reminder_per_number",
            ),
        ]

    def __str__(self) -> str:
        return f"WhatsAppJoinReminder({self.user_id}, #{self.reminder_number})"
