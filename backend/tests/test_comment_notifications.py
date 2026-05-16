"""Tests for the comment-related notification paths.

Covers both COMMENT_REPLY (someone replied to your comment) and
EVENT_COMMENT (someone commented on an event you host/co-host).
Extracted out of test_in_app_notifications and test_event_comments
to keep those files under the 500-line cap.
"""

import json

import pytest
from community.models import Event, EventComment, EventRSVP, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from notifications.service import notify_comment_reply, notify_event_comment
from users.models import User

from tests.conftest import future_iso


@pytest.mark.django_db
class TestNotifyCommentReply:
    def test_notifies_parent_author(self, test_user, db):
        replier = User.objects.create_user(
            phone_number="+12025550707",
            password="replierpass",
            display_name="Replier",
        )
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        parent = EventComment.objects.create(event=event, author=test_user, body="parent")
        reply = EventComment.objects.create(
            event=event, author=replier, body="reply", parent=parent
        )
        notify_comment_reply(reply)
        notifs = Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.COMMENT_REPLY
        )
        assert notifs.count() == 1
        n = notifs.first()
        assert n.event_id == event.id
        assert n.related_user_id == replier.id
        assert "replier" in n.message.lower() or "Replier" in n.message

    def test_no_self_notify(self, test_user, db):
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        parent = EventComment.objects.create(event=event, author=test_user, body="p")
        reply = EventComment.objects.create(event=event, author=test_user, body="r", parent=parent)
        notify_comment_reply(reply)
        assert (
            Notification.objects.filter(
                recipient=test_user, notification_type=NotificationType.COMMENT_REPLY
            ).count()
            == 0
        )

    def test_noop_for_top_level(self, test_user, db):
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        comment = EventComment.objects.create(event=event, author=test_user, body="top")
        notify_comment_reply(comment)
        assert (
            Notification.objects.filter(notification_type=NotificationType.COMMENT_REPLY).count()
            == 0
        )


@pytest.mark.django_db
class TestReplyEndpointTriggersNotification:
    def test_reply_creates_notification_for_parent_author(self, api_client, test_user, db):
        # Two RSVPd users on the same event: `author` posts the parent comment,
        # `replier` posts the reply. The reply endpoint should create a
        # COMMENT_REPLY notification for `author`.
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        author = User.objects.create_user(
            phone_number="+12025550808",
            password="authorpass",
            display_name="Author",
        )
        replier = User.objects.create_user(
            phone_number="+12025550303",
            password="replierpass",
            display_name="Replier",
        )
        EventRSVP.objects.create(event=event, user=author, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=event, user=replier, status=RSVPStatus.ATTENDING)
        parent = EventComment.objects.create(event=event, author=author, body="parent")
        replier_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(replier).access_token}"  # type: ignore
        }
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/{parent.id}/replies/",
            data=json.dumps({"body": "reply"}),
            content_type="application/json",
            **replier_headers,
        )
        assert response.status_code == 201
        notifs = Notification.objects.filter(
            recipient=author, notification_type=NotificationType.COMMENT_REPLY
        )
        assert notifs.count() == 1


@pytest.mark.django_db
class TestNotifyEventComment:
    def test_notifies_creator_and_cohosts(self, test_user, db):
        cohost = User.objects.create_user(
            phone_number="+12025551111",
            password="cohostpass",
            display_name="Cohost",
        )
        commenter = User.objects.create_user(
            phone_number="+12025552222",
            password="commenterpass",
            display_name="Commenter",
        )
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        event.co_hosts.add(cohost)
        comment = EventComment.objects.create(event=event, author=commenter, body="hi")
        notify_event_comment(comment)
        # creator + cohost both notified; commenter is not on the event team
        assert (
            Notification.objects.filter(
                recipient=test_user, notification_type=NotificationType.EVENT_COMMENT
            ).count()
            == 1
        )
        assert (
            Notification.objects.filter(
                recipient=cohost, notification_type=NotificationType.EVENT_COMMENT
            ).count()
            == 1
        )
        n = Notification.objects.filter(recipient=test_user).first()
        assert n.event_id == event.id
        assert n.related_user_id == commenter.id
        assert "commenter" in n.message.lower() or "Commenter" in n.message

    def test_no_self_notify_when_creator_comments(self, test_user, db):
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        comment = EventComment.objects.create(event=event, author=test_user, body="my own event")
        notify_event_comment(comment)
        assert (
            Notification.objects.filter(notification_type=NotificationType.EVENT_COMMENT).count()
            == 0
        )

    def test_no_self_notify_when_cohost_comments(self, test_user, db):
        cohost = User.objects.create_user(
            phone_number="+12025553333",
            password="cohostpass",
            display_name="Cohost",
        )
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        event.co_hosts.add(cohost)
        comment = EventComment.objects.create(event=event, author=cohost, body="hi team")
        notify_event_comment(comment)
        # Only the creator gets notified; the cohost author does not.
        notifs = Notification.objects.filter(notification_type=NotificationType.EVENT_COMMENT)
        assert notifs.count() == 1
        assert notifs.first().recipient_id == test_user.id

    def test_noop_for_replies(self, test_user, db):
        replier = User.objects.create_user(
            phone_number="+12025554444",
            password="pass",
            display_name="Replier",
        )
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        parent = EventComment.objects.create(event=event, author=test_user, body="parent")
        reply = EventComment.objects.create(
            event=event, author=replier, body="reply", parent=parent
        )
        notify_event_comment(reply)
        # Replies don't trigger EVENT_COMMENT (they trigger COMMENT_REPLY instead).
        assert (
            Notification.objects.filter(notification_type=NotificationType.EVENT_COMMENT).count()
            == 0
        )


@pytest.mark.django_db
class TestPostCommentEndpointTriggersNotification:
    def test_top_level_post_notifies_creator(self, api_client, test_user, db):
        commenter = User.objects.create_user(
            phone_number="+12025555555",
            password="pass",
            display_name="Commenter",
        )
        event = Event.objects.create(
            title="E",
            start_datetime=future_iso(days=10),
            created_by=test_user,
        )
        EventRSVP.objects.create(event=event, user=commenter, status=RSVPStatus.ATTENDING)
        commenter_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(commenter).access_token}"  # type: ignore
        }
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "first post"}),
            content_type="application/json",
            **commenter_headers,
        )
        assert response.status_code == 201
        assert (
            Notification.objects.filter(
                recipient=test_user, notification_type=NotificationType.EVENT_COMMENT
            ).count()
            == 1
        )
