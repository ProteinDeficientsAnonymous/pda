"""End-to-end tests for the event comments API."""

import json

import pytest
from community.models import (
    Event,
    EventComment,
    EventCommentReaction,
    EventRSVP,
    PageVisibility,
    RSVPStatus,
)
from django.utils import timezone

from tests.conftest import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        created_by=test_user,
    )


@pytest.mark.django_db
class TestGetComments:
    def test_get_empty_unauthed(self, api_client, event):
        response = api_client.get(f"/api/community/events/{event.id}/comments/")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["items"] == []
        assert body["can_post"] is False
        assert body["cannot_post_reason"] == "login_required"


@pytest.fixture
def rsvp_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550303",
        password="rsvppass123",
        display_name="RSVP Member",
    )


@pytest.fixture
def rsvp_headers(rsvp_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(rsvp_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.fixture
def event_with_rsvp(db, event, rsvp_user):
    EventRSVP.objects.create(event=event, user=rsvp_user, status=RSVPStatus.ATTENDING)
    return event


@pytest.mark.django_db
class TestPostComment:
    def test_post_requires_auth(self, api_client, event):
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "hi"}),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_post_requires_rsvp(self, api_client, event):
        # A logged-in user who is NOT the creator, not a co-host, not an admin,
        # and has no RSVP. Hosts/admins bypass the RSVP gate; bystanders don't.
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        bystander = User.objects.create_user(
            phone_number="+12025550909",
            password="bystanderpass",
            display_name="Bystander",
        )
        refresh = RefreshToken.for_user(bystander)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "hi"}),
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "comment.rsvp_required"

    def test_event_creator_can_post_without_rsvp(self, api_client, auth_headers, event):
        # test_user is event.created_by; no EventRSVP exists for them.
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            data=json.dumps({"body": "host comment"}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201, response.content
        assert response.json()["body"] == "host comment"

    def test_post_creates_comment(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": "first comment"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["body"] == "first comment"
        assert body["is_deleted"] is False
        assert body["replies"] == []
        assert body["reactions"] == []
        assert body["can_delete"] is True  # author can delete

    def test_post_rejects_empty_body(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": ""}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422

    def test_post_rejects_oversize_body(self, api_client, rsvp_headers, event_with_rsvp):
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/",
            data=json.dumps({"body": "x" * 501}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestPostReply:
    def test_reply_to_top_level_comment(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        parent = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="parent")
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{parent.id}/replies/",
            data=json.dumps({"body": "reply"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 201, response.content
        # The reply itself is returned (shape: EventCommentReplyOut)
        body = response.json()
        assert body["body"] == "reply"
        assert body["is_deleted"] is False

    def test_reply_to_reply_fails_422(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        parent = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="parent")
        reply = EventComment.objects.create(
            event=event_with_rsvp, author=rsvp_user, body="reply", parent=parent
        )
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{reply.id}/replies/",
            data=json.dumps({"body": "nested"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["code"] == "comment.reply_depth_exceeded"

    def test_reply_to_deleted_parent_404(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        parent = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="parent")
        parent.deleted_at = timezone.now()
        parent.save(update_fields=["deleted_at"])
        response = api_client.post(
            f"/api/community/events/{event_with_rsvp.id}/comments/{parent.id}/replies/",
            data=json.dumps({"body": "reply"}),
            content_type="application/json",
            **rsvp_headers,
        )
        assert response.status_code == 404


@pytest.fixture
def admin_user(db):
    from users.models import User
    from users.roles import Role

    user = User.objects.create_user(
        phone_number="+12025550404",
        password="adminpass123",
        display_name="Admin",
    )
    admin_role, _ = Role.objects.get_or_create(name="admin", defaults={"is_default": True})
    if not admin_role.is_default:
        admin_role.is_default = True
        admin_role.save(update_fields=["is_default"])
    user.roles.add(admin_role)
    return user


@pytest.fixture
def admin_headers(admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}


@pytest.mark.django_db
class TestDeleteComment:
    def test_author_can_delete_own(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="mine")
        response = api_client.delete(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/",
            **rsvp_headers,
        )
        assert response.status_code == 204
        comment.refresh_from_db()
        assert comment.deleted_at is not None

    def test_other_rsvper_cannot_delete(self, api_client, event_with_rsvp):
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        # A plain RSVP'd member who is not the event creator or admin
        bystander = User.objects.create_user(
            phone_number="+12025550606",
            password="bystanderpass",
            display_name="Bystander",
        )
        EventRSVP.objects.create(event=event_with_rsvp, user=bystander, status=RSVPStatus.ATTENDING)
        bystander_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(bystander).access_token}"
        }

        author = User.objects.create_user(
            phone_number="+12025550505",
            password="authorpass",
            display_name="Author",
        )
        EventRSVP.objects.create(event=event_with_rsvp, user=author, status=RSVPStatus.ATTENDING)
        comment = EventComment.objects.create(event=event_with_rsvp, author=author, body="theirs")
        response = api_client.delete(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/",
            **bystander_headers,
        )
        assert response.status_code == 403

    def test_event_creator_can_delete_others(self, api_client, auth_headers, event, rsvp_user):
        # event.created_by is test_user (auth_headers); comment is by rsvp_user
        comment = EventComment.objects.create(event=event, author=rsvp_user, body="theirs")
        response = api_client.delete(
            f"/api/community/events/{event.id}/comments/{comment.id}/",
            **auth_headers,
        )
        assert response.status_code == 204
        comment.refresh_from_db()
        assert comment.deleted_at is not None

    def test_admin_can_delete_others(self, api_client, admin_headers, event, rsvp_user):
        comment = EventComment.objects.create(event=event, author=rsvp_user, body="theirs")
        response = api_client.delete(
            f"/api/community/events/{event.id}/comments/{comment.id}/",
            **admin_headers,
        )
        assert response.status_code == 204

    def test_delete_requires_auth(self, api_client, event_with_rsvp, rsvp_user):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="mine")
        response = api_client.delete(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/"
        )
        assert response.status_code == 401

    def test_double_delete_is_idempotent(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        comment = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="mine")
        first = api_client.delete(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/",
            **rsvp_headers,
        )
        second = api_client.delete(
            f"/api/community/events/{event_with_rsvp.id}/comments/{comment.id}/",
            **rsvp_headers,
        )
        assert first.status_code == 204
        assert second.status_code == 204


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
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        bystander = User.objects.create_user(
            phone_number="+12025551010",
            password="bystanderpass",
            display_name="Bystander",
        )
        refresh = RefreshToken.for_user(bystander)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        comment = EventComment.objects.create(event=event, author=event.created_by, body="hi")
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/{comment.id}/reactions/",
            data=json.dumps({"emoji": "❤️"}),
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 403

    def test_rate_limit_kicks_in(self, api_client, rsvp_headers, event_with_rsvp, rsvp_user):
        """11th write in 60s should 429. Toggles back-and-forth to avoid the
        unique-constraint blocking the second create — toggle on, off, on, off..."""
        from django.core.cache import cache

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


@pytest.mark.django_db
class TestCommentVisibility:
    def test_invite_only_non_invitee_cannot_list(self, api_client, db, rsvp_user, rsvp_headers):
        creator = rsvp_user  # using rsvp_user as the event creator
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        stranger = User.objects.create_user(
            phone_number="+12025550606",
            password="strangerpass",
            display_name="Stranger",
        )
        refresh = RefreshToken.for_user(stranger)
        stranger_headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
        event = Event.objects.create(
            title="Invite-only",
            start_datetime=future_iso(days=30),
            created_by=creator,
            visibility=PageVisibility.INVITE_ONLY,
        )
        response = api_client.get(
            f"/api/community/events/{event.id}/comments/",
            **stranger_headers,
        )
        # _can_see_invite_only returns False → _enforce_event_read_visibility
        # raises Code.Event.INVITE_ONLY with status 403.
        assert response.status_code == 403

    def test_invite_only_invitee_can_list(self, api_client, db, rsvp_user, rsvp_headers):
        creator = rsvp_user
        event = Event.objects.create(
            title="Invite-only",
            start_datetime=future_iso(days=30),
            created_by=creator,
            visibility=PageVisibility.INVITE_ONLY,
        )
        # rsvp_user is the creator, so they can always see
        response = api_client.get(
            f"/api/community/events/{event.id}/comments/",
            **rsvp_headers,
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestEventOutCommentCount:
    def test_event_list_includes_comment_count(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="one")
        c2 = EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="two")
        # Deleted comments do not count.
        c2.deleted_at = timezone.now()
        c2.save(update_fields=["deleted_at"])
        response = api_client.get("/api/community/events/", **rsvp_headers)
        assert response.status_code == 200
        events_data = response.json()
        # EventListOut is returned as a bare list (see response={200: list[EventListOut]} in _events.py:155).
        target = next(e for e in events_data if e["id"] == str(event_with_rsvp.id))
        assert target["comment_count"] == 1

    def test_event_detail_includes_comment_count(
        self, api_client, rsvp_headers, event_with_rsvp, rsvp_user
    ):
        EventComment.objects.create(event=event_with_rsvp, author=rsvp_user, body="one")
        response = api_client.get(
            f"/api/community/events/{event_with_rsvp.id}/",
            **rsvp_headers,
        )
        assert response.status_code == 200
        assert response.json()["comment_count"] == 1
