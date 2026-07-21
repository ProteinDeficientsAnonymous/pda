import logging
from unittest.mock import patch

import pytest
from community.models import (
    EventRSVP,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)
from django.utils import timezone
from notifications.email_sender import SendResult
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event
from tests.conftest import future_iso, past_iso

GET_URL = "/api/community/public/my-rsvps/"


def _post_url(event):
    return f"/api/community/public/my-rsvps/{event.id}/"


@pytest.fixture
def nonmember(db):
    return make_non_member("+14155550001", "nm@example.com", name="non member")


@pytest.fixture
def official_event(db):
    return make_official_event(title="Official A")


@pytest.mark.django_db
class TestGetMyRsvps:
    def test_valid_token_returns_rsvps(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["display_name"] == "non member"
        assert len(body["rsvps"]) == 1
        assert body["rsvps"][0]["status"] == RSVPStatus.ATTENDING
        assert body["rsvps"][0]["event"]["id"] == str(official_event.id)

    def test_only_official_events_appear(self, api_client, nonmember, official_event):
        community_event = make_official_event(title="Community B", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        ids = {r["event"]["id"] for r in resp.json()["rsvps"]}
        assert ids == {str(official_event.id)}

    def test_missing_token_404(self, api_client):
        assert api_client.get(GET_URL).status_code == 404

    def test_unknown_token_404(self, api_client):
        assert api_client.get(f"{GET_URL}?token=nope").status_code == 404

    def test_revoked_token_404(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        token.revoke()
        assert api_client.get(f"{GET_URL}?token={token.token}").status_code == 404


@pytest.mark.django_db
class TestGetMyRsvpsHidesIneligibleEvents:
    """An RSVP'd event that later becomes ineligible must drop out of the list —
    otherwise its member-only details keep leaking to the token holder."""

    def _rsvp_and_list(self, api_client, nonmember, event):
        EventRSVP.objects.create(event=event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        return resp.json()["rsvps"]

    def test_cancelled_event_hidden(self, api_client, nonmember):
        event = make_official_event(title="Cancelled", status=EventStatus.CANCELLED)
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_deleted_event_hidden(self, api_client, nonmember):
        event = make_official_event(title="Deleted", status=EventStatus.DELETED)
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_draft_event_hidden(self, api_client, nonmember):
        event = make_official_event(title="Draft", status=EventStatus.DRAFT)
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_members_only_visibility_hidden(self, api_client, nonmember):
        event = make_official_event(title="Hidden", visibility=PageVisibility.MEMBERS_ONLY)
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_rsvp_disabled_hidden(self, api_client, nonmember):
        event = make_official_event(title="No RSVP", rsvp_enabled=False)
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_past_event_hidden(self, api_client, nonmember):
        event = make_official_event(title="Past", start_datetime=past_iso(days=2))
        assert self._rsvp_and_list(api_client, nonmember, event) == []

    def test_eligible_event_still_shown(self, api_client, nonmember):
        event = make_official_event(title="Live", start_datetime=future_iso(days=5))
        rsvps = self._rsvp_and_list(api_client, nonmember, event)
        assert len(rsvps) == 1
        assert rsvps[0]["event"]["id"] == str(event.id)


@pytest.mark.django_db
class TestPostMyRsvps:
    def test_update_changes_status(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["rsvp"]["status"] == RSVPStatus.ATTENDING
        rsvp = EventRSVP.objects.get(event=official_event, user=nonmember)
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_update_extends_token_keeping_same_string(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        old_expiry = token.expires_at
        token.expires_at = timezone.now() + timezone.timedelta(minutes=1)  # simulate near-expiry
        token.save(update_fields=["expires_at"])
        api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        token.refresh_from_db()
        assert token.expires_at > old_expiry - timezone.timedelta(days=1)
        # same token string still resolves
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200

    def test_update_sends_updated_email_with_manage_link(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 200
        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == nonmember.email
        assert sent["subject"] == "your rsvp was updated"
        # The emailed manage link reuses the still-valid token.
        assert token.token in sent["text"]

    def test_email_failure_does_not_roll_back_update(
        self, api_client, nonmember, official_event, fake_email_sender, caplog
    ):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")

        audit_logger = logging.getLogger("pda.audit")
        audit_logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.WARNING, logger="pda.audit"):
                resp = api_client.post(
                    f"{_post_url(official_event)}?token={token.token}",
                    {"status": RSVPStatus.ATTENDING},
                    content_type="application/json",
                )
        finally:
            audit_logger.removeHandler(caplog.handler)

        assert resp.status_code == 200
        rsvp = EventRSVP.objects.get(event=official_event, user=nonmember)
        assert rsvp.status == RSVPStatus.ATTENDING
        failures = [
            r for r in caplog.records if getattr(r, "action", None) == "public_rsvp_email_failed"
        ]
        assert len(failures) == 1

    def test_invalid_status_400(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.WAITLISTED},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_ineligible_event_404(self, api_client, nonmember):
        community_event = make_official_event(title="C", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(community_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_bad_token_404(self, api_client, official_event):
        resp = api_client.post(
            f"{_post_url(official_event)}?token=nope",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_update_broadcasts_capacity_change(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        with patch("community._public_rsvp_manage.broadcast_capacity_change") as mock_broadcast:
            api_client.post(
                f"{_post_url(official_event)}?token={token.token}",
                {"status": RSVPStatus.MAYBE},
                content_type="application/json",
            )
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == official_event.id


@pytest.mark.django_db
class TestDeleteMyRsvps:
    def test_delete_removes_rsvp(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        assert not EventRSVP.objects.filter(event=official_event, user=nonmember).exists()
        # subsequent GET no longer lists it
        listed = api_client.get(f"{GET_URL}?token={token.token}").json()["rsvps"]
        assert listed == []

    def test_delete_promotes_waitlist(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        official_event.max_attendees = 1
        official_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        waiter = make_non_member("+14155550002", "w@example.com", name="waiter")
        EventRSVP.objects.create(event=official_event, user=waiter, status=RSVPStatus.WAITLISTED)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        waiter_rsvp = EventRSVP.objects.get(event=official_event, user=waiter)
        assert waiter_rsvp.status == RSVPStatus.ATTENDING
        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == waiter.email
        assert sent["subject"] == "you're off the waitlist for official a"

    def test_delete_no_rsvp_404(self, api_client, nonmember, official_event):
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 404

    def test_delete_bad_token_404(self, api_client, official_event):
        resp = api_client.delete(f"{_post_url(official_event)}?token=nope")
        assert resp.status_code == 404

    def test_delete_broadcasts_capacity_change(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        with patch("community._public_rsvp_manage.broadcast_capacity_change") as mock_broadcast:
            api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        mock_broadcast.assert_called_once()
        assert mock_broadcast.call_args.args[0] == official_event.id


@pytest.mark.django_db
class TestPublicRsvpManageComment:
    """Verify that update_my_rsvp now honours the optional comment field."""

    def _setup(self, nonmember, official_event, status=RSVPStatus.ATTENDING):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=status)
        return NonMemberRsvpToken.issue_or_extend(nonmember)

    def _post(self, api_client, event, token, **body):
        return api_client.post(
            f"{_post_url(event)}?token={token.token}",
            body,
            content_type="application/json",
        )

    def test_going_comment_creates_event_comment(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        from community.models import EventComment

        token = self._setup(nonmember, official_event)
        resp = self._post(
            api_client,
            official_event,
            token,
            status=RSVPStatus.ATTENDING,
            comment="bringing snacks",
        )
        assert resp.status_code == 200
        comments = EventComment.objects.filter(event=official_event, author=nonmember)
        assert comments.count() == 1
        assert comments.first().body == "bringing snacks"

    def test_cant_go_comment_sends_decline_notification(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        from unittest.mock import patch

        from community.models import EventComment

        token = self._setup(nonmember, official_event, status=RSVPStatus.ATTENDING)
        with patch("community._event_rsvps.notify_rsvp_declined_note") as mock_notify:
            resp = self._post(
                api_client,
                official_event,
                token,
                status=RSVPStatus.CANT_GO,
                comment="out of town",
            )
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=official_event, author=nonmember).exists()
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["note"] == "out of town"

    def test_empty_comment_creates_nothing(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        from community.models import EventComment

        token = self._setup(nonmember, official_event)
        resp = self._post(
            api_client, official_event, token, status=RSVPStatus.ATTENDING, comment="   "
        )
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=official_event, author=nonmember).exists()

    def test_no_comment_creates_nothing(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        from community.models import EventComment

        token = self._setup(nonmember, official_event)
        resp = self._post(api_client, official_event, token, status=RSVPStatus.ATTENDING)
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=official_event, author=nonmember).exists()

    def test_oversized_comment_is_rejected(
        self, api_client, nonmember, official_event, fake_email_sender
    ):
        token = self._setup(nonmember, official_event)
        resp = self._post(
            api_client,
            official_event,
            token,
            status=RSVPStatus.ATTENDING,
            comment="x" * 301,
        )
        assert resp.status_code == 422
