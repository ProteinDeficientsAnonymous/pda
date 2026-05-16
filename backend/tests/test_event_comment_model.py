"""Unit tests for the EventComment and EventCommentReaction models."""

import pytest
from community.models import (
    Event,
    EventComment,
    EventCommentReaction,
    ReactionEmoji,
)
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestEventCommentModel:
    def test_create_top_level_comment(self, test_user):
        event = Event.objects.create(
            title="Test Event",
            start_datetime="2030-01-01T00:00:00Z",
            created_by=test_user,
        )
        comment = EventComment.objects.create(
            event=event,
            author=test_user,
            body="hello world",
        )
        assert comment.id is not None
        assert comment.parent is None
        assert comment.deleted_at is None
        assert comment.body == "hello world"

    def test_reply_to_top_level_comment(self, test_user):
        event = Event.objects.create(
            title="Test Event",
            start_datetime="2030-01-01T00:00:00Z",
            created_by=test_user,
        )
        parent = EventComment.objects.create(event=event, author=test_user, body="parent")
        reply = EventComment.objects.create(
            event=event, author=test_user, body="reply", parent=parent
        )
        reply.full_clean()
        assert reply.parent_id == parent.id

    def test_reply_to_reply_fails_clean(self, test_user):
        event = Event.objects.create(
            title="Test Event",
            start_datetime="2030-01-01T00:00:00Z",
            created_by=test_user,
        )
        parent = EventComment.objects.create(event=event, author=test_user, body="parent")
        reply = EventComment.objects.create(
            event=event, author=test_user, body="reply", parent=parent
        )
        nested = EventComment(event=event, author=test_user, body="nested", parent=reply)
        with pytest.raises(ValidationError):
            nested.full_clean()


@pytest.mark.django_db
class TestEventCommentReactionModel:
    def test_create_reaction(self, test_user):
        event = Event.objects.create(
            title="Test Event",
            start_datetime="2030-01-01T00:00:00Z",
            created_by=test_user,
        )
        comment = EventComment.objects.create(event=event, author=test_user, body="hi")
        reaction = EventCommentReaction.objects.create(
            comment=comment, user=test_user, emoji=ReactionEmoji.HEART
        )
        assert reaction.id is not None

    def test_unique_constraint(self, test_user):
        event = Event.objects.create(
            title="Test Event",
            start_datetime="2030-01-01T00:00:00Z",
            created_by=test_user,
        )
        comment = EventComment.objects.create(event=event, author=test_user, body="hi")
        EventCommentReaction.objects.create(
            comment=comment, user=test_user, emoji=ReactionEmoji.HEART
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            EventCommentReaction.objects.create(
                comment=comment, user=test_user, emoji=ReactionEmoji.HEART
            )
