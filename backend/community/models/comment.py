"""Event comment and reaction models.

Comments attach to Events with one level of reply nesting (a reply cannot
have a reply). Reactions are emoji-toggles on comments. See the spec at
docs/superpowers/specs/2026-05-15-event-comments-reactions-design.md.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models

if TYPE_CHECKING:
    from django.db.models import Manager


class ReactionEmoji(models.TextChoices):
    HEART = "❤️", "Heart"
    JOY = "😂", "Joy"
    SEEDLING = "🌱", "Seedling"
    FIRE = "🔥", "Fire"
    THUMBS_UP = "👍", "Thumbs up"
    SOB = "😭", "Sob"


class EventComment(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        author_id: uuid.UUID
        parent_id: uuid.UUID | None
        replies: Manager[EventComment]
        reactions: Manager[EventCommentReaction]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "community.Event",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="event_comments",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    body = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "-created_at"]),
            models.Index(fields=["parent", "created_at"]),
        ]

    def clean(self) -> None:
        super().clean()
        if self.parent_id is not None and self.parent.parent_id is not None:
            raise ValidationError({"parent": "Replies cannot have replies (depth = 1)."})
        if self.parent_id is not None and self.parent.event_id != self.event_id:
            raise ValidationError({"parent": "Reply must be in the same event as its parent."})

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __str__(self) -> str:
        return f"Comment {self.id} on event {self.event_id}"


class EventCommentReaction(models.Model):
    if TYPE_CHECKING:
        comment_id: uuid.UUID
        user_id: uuid.UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        EventComment,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="event_comment_reactions",
    )
    emoji = models.CharField(
        max_length=8,
        choices=ReactionEmoji.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "user", "emoji"],
                name="unique_comment_user_emoji_reaction",
            ),
        ]
        indexes = [
            models.Index(fields=["comment", "emoji"]),
        ]

    def __str__(self) -> str:
        return f"{self.emoji} by {self.user_id} on comment {self.comment_id}"
