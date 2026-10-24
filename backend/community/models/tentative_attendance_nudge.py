import uuid

from django.db import models


class TentativeAttendanceNudge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="attendance_nudges"
    )
    nudge_number = models.PositiveSmallIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "nudge_number"],
                name="unique_tentative_attendance_nudge_per_number",
            ),
        ]

    def __str__(self) -> str:
        return f"TentativeAttendanceNudge({self.user_id}, #{self.nudge_number})"
