"""EventPoll, PollOption, PollVote models."""

import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models import Manager


class EventPoll(models.Model):
    if TYPE_CHECKING:
        created_by_id: uuid.UUID | None
        finalized_by_id: uuid.UUID | None
        winning_option_id: uuid.UUID | None
        options: "Manager[PollOption]"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField("community.Event", on_delete=models.CASCADE, related_name="poll")
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_polls",
    )
    is_active = models.BooleanField(default=True)
    winning_option = models.ForeignKey(
        "community.PollOption",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    finalized_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finalized_event_polls",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Poll for {self.event.title}"


class PollOption(models.Model):
    if TYPE_CHECKING:
        poll_id: uuid.UUID
        votes: "Manager[PollVote]"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(EventPoll, on_delete=models.CASCADE, related_name="options")
    datetime = models.DateTimeField()
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "community"
        ordering = ["datetime"]
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "datetime"], name="unique_poll_option_datetime"
            ),
        ]

    def __str__(self):
        return f"{self.poll.event.title}: {self.datetime:%Y-%m-%d %H:%M}"


class PollVote(models.Model):
    if TYPE_CHECKING:
        user_id: uuid.UUID
        option_id: uuid.UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="poll_votes")
    availability = models.CharField(max_length=10)
    voted_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        ordering = ["-voted_at"]
        constraints = [
            models.UniqueConstraint(fields=["option", "user"], name="unique_poll_vote"),
        ]

    def __str__(self):
        return f"{self.user} → {self.option}: {self.availability}"
