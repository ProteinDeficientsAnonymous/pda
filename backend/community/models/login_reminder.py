import uuid

from django.db import models


class LoginReminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="login_reminders")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"LoginReminder({self.user_id}, {self.sent_at})"
