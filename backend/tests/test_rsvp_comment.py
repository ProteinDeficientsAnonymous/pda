from unittest.mock import patch

import pytest
from community.models import Event, EventComment, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="RSVP Event",
        description="An event with RSVPs enabled",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        location="Community Space",
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def member(db):
    return User.objects.create_user(
        phone_number="+12025550302", password="pw", first_name="Member", last_name=""
    )


@pytest.fixture
def member_headers(member):
    refresh = RefreshToken.for_user(member)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _rsvp(api_client, headers, event, status, comment=None):
    payload = {"status": status}
    if comment is not None:
        payload["comment"] = comment
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        payload,
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestRSVPCommentRouting:
    def test_going_comment_creates_comment(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(
            api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "bringing snacks"
        )
        assert resp.status_code == 200
        comments = EventComment.objects.filter(event=rsvp_event, author=member)
        assert comments.count() == 1
        assert comments.first().body == "bringing snacks"

    def test_maybe_comment_creates_comment(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.MAYBE, "might be late")
        assert resp.status_code == 200
        assert (
            EventComment.objects.filter(
                event=rsvp_event, author=member, body="might be late"
            ).count()
            == 1
        )

    def test_going_comment_notifies_host(
        self, api_client, member_headers, member, rsvp_event, test_user
    ):
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "yo")
        assert (
            Notification.objects.filter(
                recipient=test_user, notification_type=NotificationType.EVENT_COMMENT
            ).count()
            == 1
        )

    def test_cant_go_comment_creates_no_comment_but_notifies_host(
        self, api_client, member_headers, member, rsvp_event, test_user
    ):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.CANT_GO, "out of town")
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()
        notifs = Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.RSVP_DECLINED_NOTE
        )
        assert notifs.count() == 1
        assert "out of town" in notifs.first().message

    def test_no_comment_creates_nothing(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING)
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()
        assert not Notification.objects.filter(
            notification_type=NotificationType.RSVP_DECLINED_NOTE
        ).exists()

    def test_empty_comment_creates_nothing(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "   ")
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()

    def test_status_only_edit_creates_no_new_comment(
        self, api_client, member_headers, member, rsvp_event
    ):
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "first comment")
        assert EventComment.objects.filter(event=rsvp_event, author=member).count() == 1
        # Re-RSVP with no comment key (an edit) — must not post another comment.
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.MAYBE)
        assert EventComment.objects.filter(event=rsvp_event, author=member).count() == 1

    def test_comment_post_failure_does_not_fail_the_rsvp(
        self, api_client, member_headers, member, rsvp_event
    ):
        with patch("community._event_rsvps.notify_event_comment", side_effect=RuntimeError("boom")):
            resp = _rsvp(
                api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "bringing snacks"
            )
        assert resp.status_code == 200
        assert EventComment.objects.filter(event=rsvp_event, author=member).exists()

    def test_rsvp_endpoint_is_rate_limited_at_10_per_minute(
        self, api_client, member_headers, member, rsvp_event
    ):
        # 10/min matches post_comment's own rate limit — comments posted via
        # RSVP notes must not get a more generous budget than the comment
        # endpoint itself.
        last_status = None
        for i in range(12):
            resp = _rsvp(
                api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, f"comment {i}"
            )
            last_status = resp.status_code
            if last_status == 429:
                break

        assert last_status == 429
        assert EventComment.objects.filter(event=rsvp_event, author=member).count() <= 10
