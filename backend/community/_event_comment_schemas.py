"""Pydantic schemas for the event comments API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReactorOut(BaseModel):
    user_id: str
    name: str
    photo_url: str


class CommentReactionSummaryOut(BaseModel):
    emoji: str
    count: int
    reacted_by_me: bool
    reactors: list[ReactorOut] = []


class EventCommentReplyOut(BaseModel):
    id: str
    author_id: str
    author_display_name: str
    author_photo_url: str
    body: str  # "" when is_deleted is True
    is_deleted: bool
    created_at: datetime
    reactions: list[CommentReactionSummaryOut]
    can_delete: bool


class EventCommentOut(EventCommentReplyOut):
    replies: list[EventCommentReplyOut]


class EventCommentListOut(BaseModel):
    items: list[EventCommentOut]
    can_post: bool
    cannot_post_reason: Literal["login_required", "rsvp_required"] | None = None


class CommentBodyIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=500)


class ReactionToggleIn(BaseModel):
    emoji: str
