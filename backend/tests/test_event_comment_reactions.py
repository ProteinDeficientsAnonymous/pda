import json

import pytest
from community.models import Event, EventComment, EventCommentReaction, EventRSVP, RSVPStatus
from django.core.cache import cache
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        created_by=test_user,
    )


@pytest.fixture
def rsvp_user(db):
    return User.objects.create_user(
        phone_number="+12025550303",
        password="rsvppass123",
        first_name="RSVP",
        last_name="Member",
    )


@pytest.fixture
def rsvp_headers(rsvp_user):
    refresh = RefreshToken.for_user(rsvp_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def event_with_rsvp(db, event, rsvp_user):
    EventRSVP.objects.create(event=event, user=rsvp_user, status=RSVPStatus.ATTENDING)
    return event


@pytest.mark.django_db
class TestReactionToggle:
    def test_first_toggle_creates(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 200, response.content
        body = response.json()
        hearts = [r for r in body["reactions"] if r["emoji"] == "❤️"]
        assert len(hearts) == 1
        assert hearts[0]["count"] == 1
        assert hearts[0]["reacted_by_me"] is True

    def test_second_toggle_removes(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        EventCommentReaction.objects.create(comment=comment, user=rsvp_user, emoji="❤️")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 200
        assert response.json()["reactions"] == []

    def test_stacking_different_emojis(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **rsvp_headers,
        )
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "🔥"}),
            content_type="application/json",
            **rsvp_headers,
        )
        emojis = {r["emoji"] for r in response.json()["reactions"]}
        assert emojis == {"❤️", "🔥"}

    def test_invalid_emoji(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "🦊"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["code"] == "comment.invalid_emoji"

    def test_reaction_requires_rsvp(self, api_client, event):
        # A bystander (not creator, not co-host, not admin, no RSVP).
        bystander = User.objects.create_user(
            phone_number="+12025551010",
            password="bystanderpass",
            first_name="Bystander",
        )
        refresh = RefreshToken.for_user(bystander)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        comment = EventComment.objects.create(event=event, author=event.created_by, body="hi")
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_reaction_notifies_comment_author(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        other_user = User.objects.create_user(
            phone_number="+12025552020",
            password="otherpass123",
            first_name="Other",
            last_name="Member",
        )
        EventRSVP.objects.create(
            event=event_with_rsvp, user=other_user, status=RSVPStatus.ATTENDING
        )
        other_refresh = RefreshToken.for_user(other_user)
        other_headers = {"HTTP_AUTHORIZATION": f"Bearer {other_refresh.access_token}"}  # type: ignore
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200, response.content
        notification = Notification.objects.get(recipient=rsvp_user)
        assert notification.notification_type == NotificationType.COMMENT_REACTION
        assert notification.related_user_id == other_user.id  # ty: ignore[unresolved-attribute]

    def test_self_reaction_does_not_notify(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 200, response.content
        assert not Notification.objects.filter(
            recipient=rsvp_user, notification_type=NotificationType.COMMENT_REACTION
        ).exists()

    def test_removing_reaction_does_not_notify(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        other_user = User.objects.create_user(
            phone_number="+12025552021",
            password="otherpass123",
            first_name="Other",
            last_name="Member",
        )
        EventRSVP.objects.create(
            event=event_with_rsvp, user=other_user, status=RSVPStatus.ATTENDING
        )
        other_refresh = RefreshToken.for_user(other_user)
        other_headers = {"HTTP_AUTHORIZATION": f"Bearer {other_refresh.access_token}"}  # type: ignore
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        EventCommentReaction.objects.create(comment=comment, user=other_user, emoji="❤️")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200, response.content
        assert not Notification.objects.filter(
            recipient=rsvp_user, notification_type=NotificationType.COMMENT_REACTION
        ).exists()

    def test_rate_limit_kicks_in(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        """11th write in 60s should 429. Toggles back-and-forth to avoid the
        unique-constraint blocking the second create — toggle on, off, on, off..."""
        cache.clear()
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="hi")
        url = f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/reactions/"
        for _ in range(10):
            r = api_client.post(
                url,
                data=json.dumps({"emoji": "❤️"}),
                content_type="application/json",
                **rsvp_headers,
            )
            assert r.status_code == 200, r.content
        # 11th request hits the limit
        r = api_client.post(
            url,
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert r.status_code == 429
        assert r.json()["detail"][0]["code"] == "rate.limited"
