import secrets
import uuid
from typing import TYPE_CHECKING

from django.db import models

from community.models.survey import Survey


class EventFeedbackRequest(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        user_id: uuid.UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "community.Event", on_delete=models.CASCADE, related_name="feedback_requests"
    )
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="feedback_requests"
    )
    token = models.CharField(max_length=64, unique=True)
    first_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    responded_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"], name="unique_feedback_request_per_event_user"
            ),
        ]

    def __str__(self) -> str:
        return f"EventFeedbackRequest({self.event_id}, {self.user_id})"

    @staticmethod
    def new_token() -> str:
        return secrets.token_urlsafe(32)


def feedback_survey_for(event_type: str) -> Survey | None:
    return Survey.objects.filter(feedback_event_type=event_type).first()
