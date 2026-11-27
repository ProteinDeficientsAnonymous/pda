import uuid

from django.db import models


class ClubReminderStage(models.TextChoices):
    EARLY = "early", "Early"
    WEEK = "week", "Week"
    FINAL = "final", "Final"


class ClubEventReminder(models.Model):
    """Dedup record: one reminder stage sent to a club's reps for a target month."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club = models.ForeignKey(
        "community.Club", on_delete=models.CASCADE, related_name="event_reminders"
    )
    month = models.DateField()
    stage = models.CharField(max_length=10, choices=ClubReminderStage.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        constraints = [
            models.UniqueConstraint(
                fields=["club", "month", "stage"], name="club_event_reminder_unique"
            )
        ]
