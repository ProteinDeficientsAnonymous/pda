"""Tests for the public (non-member) RSVP submission endpoint.

POST /api/community/public/events/{event_id}/rsvp/ — no auth. Backs each RSVP
with a non-member User row so the existing RSVP machinery is reused, issues a
scoped NonMemberRsvpToken, and emails a confirmation with a /my-rsvps magic link.

Capacity / waitlist / robustness cases live in test_public_rsvp_capacity.py.
"""

from unittest.mock import patch

import pytest
from community._validation import Code
from community.models import EventRSVP, EventStatus, EventType, PageVisibility, RSVPStatus
from users.models import NonMemberRsvpToken, User

from tests._public_rsvp_helpers import (
    URL_TEMPLATE,
    first_code,
    make_non_member,
    make_official_event,
    payload,
    post,
)
from tests.conftest import future_iso, past_iso


@pytest.fixture
def official_event(db):
    return make_official_event(
        location="123 Vegan Way", whatsapp_link="https://chat.whatsapp.com/abc123"
    )


@pytest.mark.django_db
class TestPublicRsvpHappyPath:
    def test_creates_user_rsvp_token_and_emails(
        self, api_client, official_event, fake_email_sender
    ):
        response = post(api_client, official_event)

        assert response.status_code == 200
        body = response.json()
        assert body["rsvp"]["status"] == RSVPStatus.ATTENDING
        assert body["rsvp"]["has_plus_one"] is False
        # Token must NOT leak into the response — email only.
        assert "token" not in body
        assert "token" not in body["rsvp"]

        user = User.objects.get(phone_number="+14155550123")
        assert user.is_member is False
        assert user.email == "sam@example.com"
        assert user.full_name == "Sam Green"
        assert not user.has_usable_password()
        assert EventRSVP.objects.filter(event=official_event, user=user).count() == 1
        assert NonMemberRsvpToken.objects.filter(user=user).count() == 1

        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "sam@example.com"
        assert "you're in" in sent["subject"]
        token = NonMemberRsvpToken.objects.get(user=user)
        assert token.token in sent["text"]

    def test_broadcasts_event_update(self, api_client, official_event, fake_email_sender):
        with patch("community._public_rsvp_submit.broadcast_capacity_change") as mock_broadcast:
            post(api_client, official_event)
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == official_event.id

    def test_response_exposes_gated_event_details(
        self, api_client, official_event, fake_email_sender
    ):
        # A successful RSVP entitles the non-member to the gated fields.
        response = post(api_client, official_event)
        event_out = response.json()["event"]
        assert event_out["location"] == "123 Vegan Way"
        assert event_out["whatsapp_link"] == "https://chat.whatsapp.com/abc123"


@pytest.mark.django_db
class TestPublicRsvpDedup:
    def test_returning_by_phone_reuses_row(self, api_client, official_event, fake_email_sender):
        existing = make_non_member("+14155550123", "old@example.com")

        response = post(api_client, official_event, email="new@example.com")

        assert response.status_code == 200
        assert User.objects.filter(phone_number="+14155550123").count() == 1
        existing.refresh_from_db()
        # Email already set → never overwritten.
        assert existing.email == "old@example.com"
        assert NonMemberRsvpToken.objects.filter(user=existing).count() == 1

    def test_returning_by_phone_saves_email_if_blank(
        self, api_client, official_event, fake_email_sender
    ):
        existing = make_non_member("+14155550123", None)

        post(api_client, official_event, email="sam@example.com")

        existing.refresh_from_db()
        assert existing.email == "sam@example.com"

    def test_returning_by_email_reuses_row(self, api_client, official_event, fake_email_sender):
        existing = make_non_member("+14155550999", "sam@example.com")

        response = post(api_client, official_event, phone_number="+14155550123")

        assert response.status_code == 200
        assert User.objects.filter(email="sam@example.com").count() == 1
        # Phone already set → not overwritten; no new user for the new phone.
        assert not User.objects.filter(phone_number="+14155550123").exists()
        assert EventRSVP.objects.filter(user=existing).count() == 1

    def test_both_match_same_row_no_change(self, api_client, official_event, fake_email_sender):
        existing = make_non_member("+14155550123", "sam@example.com")

        response = post(api_client, official_event)

        assert response.status_code == 200
        assert User.objects.filter(is_member=False).count() == 1
        existing.refresh_from_db()
        assert existing.email == "sam@example.com"

    def test_phone_and_email_match_different_rows_phone_wins(
        self, api_client, official_event, fake_email_sender
    ):
        phone_row = make_non_member("+14155550123", "phone@example.com", name="Phone Row")
        email_row = make_non_member("+14155550888", "sam@example.com", name="Email Row")

        response = post(api_client, official_event)

        assert response.status_code == 200
        # Phone wins: RSVP attached to the phone-matched row, email untouched.
        assert EventRSVP.objects.filter(user=phone_row).exists()
        assert not EventRSVP.objects.filter(user=email_row).exists()
        phone_row.refresh_from_db()
        assert phone_row.email == "phone@example.com"

    def test_same_phone_twice_yields_one_user(self, api_client, official_event, fake_email_sender):
        post(api_client, official_event)
        post(api_client, official_event, status=RSVPStatus.MAYBE)

        assert User.objects.filter(phone_number="+14155550123").count() == 1
        user = User.objects.get(phone_number="+14155550123")
        assert EventRSVP.objects.filter(event=official_event, user=user).count() == 1
        assert EventRSVP.objects.get(event=official_event, user=user).status == RSVPStatus.MAYBE

    def test_archived_email_holder_does_not_block_create(
        self, api_client, official_event, fake_email_sender
    ):
        # An archived user holding the submitted email is ignored by the lookups;
        # the create path must survive the unique-email collision and RSVP anyway.
        from django.utils import timezone

        archived = make_non_member("+14155550777", "sam@example.com", name="Archived")
        archived.archived_at = timezone.now()
        archived.save(update_fields=["archived_at"])

        response = post(api_client, official_event)

        assert response.status_code == 200
        new_user = User.objects.get(phone_number="+14155550123")
        assert new_user.pk != archived.pk
        # Email dropped to avoid the collision; RSVP still created.
        assert new_user.email is None
        assert EventRSVP.objects.filter(user=new_user).exists()

    def test_multiple_rsvps_reuse_the_same_token(
        self, api_client, official_event, fake_email_sender
    ):
        other_event = make_official_event(
            title="Second Official", start_datetime=future_iso(days=20)
        )
        post(api_client, official_event)
        first_token = NonMemberRsvpToken.objects.get(user__phone_number="+14155550123").token
        post(api_client, other_event)

        user = User.objects.get(phone_number="+14155550123")
        assert EventRSVP.objects.filter(user=user).count() == 2
        tokens = NonMemberRsvpToken.objects.filter(user=user)
        assert tokens.count() == 1
        assert tokens.first().token == first_token


@pytest.mark.django_db
class TestPublicRsvpMemberCollision:
    def test_phone_belongs_to_member(self, api_client, official_event, fake_email_sender):
        User.objects.create_user(
            phone_number="+14155550123", first_name="A", last_name="Member", is_member=True
        )

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert first_code(response) == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()
        fake_email_sender.send.assert_not_called()

    def test_email_belongs_to_member(self, api_client, official_event, fake_email_sender):
        User.objects.create_user(
            phone_number="+14155550555",
            first_name="A",
            last_name="Member",
            email="sam@example.com",
            is_member=True,
        )

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert first_code(response) == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()

    def test_member_email_match_is_case_insensitive(
        self, api_client, official_event, fake_email_sender
    ):
        # A member whose email is stored mixed-case must still trip the gate when
        # the RSVP submits the same address in different case.
        User.objects.create_user(
            phone_number="+14155550555",
            first_name="A",
            last_name="Member",
            email="Sam@Example.COM",
            is_member=True,
        )

        response = post(api_client, official_event, email="sam@example.com")

        assert response.status_code == 409
        assert first_code(response) == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()

    def test_member_created_with_non_canonical_phone_still_trips_gate(
        self, api_client, official_event, fake_email_sender
    ):
        # User.save() now canonicalizes on every write (Issue 975), so even a
        # member row constructed with a loosely-formatted phone number is
        # stored as E.164 and the RSVP phone-match gate still catches it.
        User.objects.create_user(
            phone_number="(415) 555-0123", first_name="A", last_name="Member", is_member=True
        )

        response = post(api_client, official_event, email="different@example.com")

        assert response.status_code == 409
        assert first_code(response) == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN
        assert not EventRSVP.objects.exists()


@pytest.mark.django_db
class TestPublicRsvpEventGating:
    def test_community_event(self, api_client, fake_email_sender):
        event = make_official_event(event_type=EventType.COMMUNITY)
        assert post(api_client, event).status_code == 404

    def test_members_only(self, api_client, fake_email_sender):
        event = make_official_event(visibility=PageVisibility.MEMBERS_ONLY)
        assert post(api_client, event).status_code == 404

    def test_invite_only(self, api_client, fake_email_sender):
        event = make_official_event(visibility=PageVisibility.INVITE_ONLY)
        assert post(api_client, event).status_code == 404

    def test_rsvp_disabled(self, api_client, fake_email_sender):
        event = make_official_event(rsvp_enabled=False)
        assert post(api_client, event).status_code == 404

    def test_draft(self, api_client, fake_email_sender):
        event = make_official_event(status=EventStatus.DRAFT)
        assert post(api_client, event).status_code == 404

    def test_cancelled(self, api_client, fake_email_sender):
        event = make_official_event(status=EventStatus.CANCELLED)
        assert post(api_client, event).status_code == 404

    def test_past(self, api_client, fake_email_sender):
        event = make_official_event(start_datetime=past_iso(days=2), end_datetime=past_iso(days=2))
        assert post(api_client, event).status_code == 404

    def test_nonexistent(self, api_client, fake_email_sender):
        import uuid

        response = api_client.post(
            URL_TEMPLATE.format(event_id=uuid.uuid4()),
            payload(),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_gating_returns_not_found_code(self, api_client, fake_email_sender):
        event = make_official_event(event_type=EventType.COMMUNITY)
        response = post(api_client, event)
        assert first_code(response) == Code.Event.NOT_FOUND


@pytest.mark.django_db
class TestPublicRsvpValidation:
    def test_missing_name(self, api_client, official_event):
        response = api_client.post(
            URL_TEMPLATE.format(event_id=official_event.id),
            {k: v for k, v in payload().items() if k != "first_name"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_blank_name(self, api_client, official_event):
        response = post(api_client, official_event, first_name="   ")
        assert response.status_code == 422

    def test_missing_email(self, api_client, official_event):
        response = api_client.post(
            URL_TEMPLATE.format(event_id=official_event.id),
            {k: v for k, v in payload().items() if k != "email"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_invalid_email(self, api_client, official_event):
        response = post(api_client, official_event, email="not-an-email")
        assert response.status_code == 422

    def test_invalid_phone(self, api_client, official_event):
        response = post(api_client, official_event, phone_number="123")
        assert response.status_code == 422
        assert first_code(response) == Code.Phone.INVALID

    def test_invalid_status(self, api_client, official_event):
        response = post(api_client, official_event, status=RSVPStatus.WAITLISTED)
        assert response.status_code == 400
        assert first_code(response) == Code.Event.RSVP_INVALID_STATUS


@pytest.mark.django_db
class TestPublicRsvpHoneypot:
    def test_honeypot_returns_decoy_no_side_effects(
        self, api_client, official_event, fake_email_sender
    ):
        response = post(api_client, official_event, website="http://spam.example")

        assert response.status_code == 200
        assert not User.objects.filter(phone_number="+14155550123").exists()
        assert not EventRSVP.objects.exists()
        assert not NonMemberRsvpToken.objects.exists()
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestPublicRsvpRateLimit:
    def test_sixth_request_is_limited(self, api_client, official_event, fake_email_sender):
        for i in range(5):
            r = post(
                api_client, official_event, phone_number=f"+1415555010{i}", email=f"u{i}@e.com"
            )
            assert r.status_code == 200, r.content
        sixth = post(api_client, official_event, phone_number="+14155550199", email="u9@e.com")
        assert sixth.status_code == 429
        assert first_code(sixth) == Code.Rate.LIMITED


@pytest.mark.django_db
class TestPublicRsvpToken:
    def test_submit_response_includes_rsvp_token(
        self, api_client, official_event, fake_email_sender
    ):
        response = post(api_client, official_event)
        assert response.status_code == 200, response.content
        body = response.json()
        assert isinstance(body["rsvp_token"], str)
        assert len(body["rsvp_token"]) > 20  # secrets.token_urlsafe(32) output

        assert NonMemberRsvpToken.objects.filter(token=body["rsvp_token"]).exists()


@pytest.mark.django_db
class TestPublicRsvpComment:
    def test_going_comment_creates_event_comment(
        self, api_client, official_event, fake_email_sender
    ):
        response = post(api_client, official_event, comment="bringing snacks")
        assert response.status_code == 200
        from community.models import EventComment

        user = User.objects.get(phone_number="+14155550123")
        comments = EventComment.objects.filter(event=official_event, author=user)
        assert comments.count() == 1
        assert comments.first().body == "bringing snacks"

    def test_cant_go_comment_sends_decline_notification(
        self, api_client, official_event, fake_email_sender
    ):
        """Can't Go is not available for first-time public RSVPs, but the endpoint
        must handle it gracefully if ever called directly: a decline-note notification
        is sent and no public comment is created."""
        from community.models import EventComment
        from notifications.models import Notification, NotificationType

        host = official_event.created_by
        resp = api_client.post(
            URL_TEMPLATE.format(event_id=official_event.id),
            {
                **payload(),
                "status": RSVPStatus.CANT_GO,
                "comment": "out of town",
            },
            content_type="application/json",
        )
        # The endpoint accepts any status; validation only blocks WAITLISTED.
        assert resp.status_code == 200
        user = User.objects.get(phone_number="+14155550123")
        assert not EventComment.objects.filter(event=official_event, author=user).exists()
        if host:
            assert Notification.objects.filter(
                recipient=host, notification_type=NotificationType.RSVP_DECLINED_NOTE
            ).exists()

    def test_empty_comment_creates_nothing(self, api_client, official_event, fake_email_sender):
        from community.models import EventComment

        response = post(api_client, official_event, comment="   ")
        assert response.status_code == 200
        user = User.objects.get(phone_number="+14155550123")
        assert not EventComment.objects.filter(event=official_event, author=user).exists()

    def test_no_comment_creates_nothing(self, api_client, official_event, fake_email_sender):
        from community.models import EventComment

        response = post(api_client, official_event)
        assert response.status_code == 200
        user = User.objects.get(phone_number="+14155550123")
        assert not EventComment.objects.filter(event=official_event, author=user).exists()

    def test_oversized_comment_is_rejected(self, api_client, official_event, fake_email_sender):
        response = post(api_client, official_event, comment="x" * 301)
        assert response.status_code == 422
