import uuid

from django.db import models


class AttendanceMilestone(models.TextChoices):
    M10 = "m10", "10 months"
    M11 = "m11", "11 months"
    M11_5 = "m11_5", "11.5 months"
    M12 = "m12", "12 months"


class AttendanceReminder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="attendance_reminders"
    )
    milestone = models.CharField(max_length=10, choices=AttendanceMilestone.choices)
    anchor_date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "milestone", "anchor_date"],
                name="unique_attendance_reminder_per_anchor",
            ),
        ]

    def __str__(self) -> str:
        return f"AttendanceReminder({self.user_id}, {self.milestone}, {self.anchor_date})"
