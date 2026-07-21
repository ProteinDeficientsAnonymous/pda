"""Tests for the public rsvp phone-check endpoint.

POST /api/community/public/events/{event_id}/rsvp-phone-check/ — no auth. Lets
the frontend ask "what should happen for this phone number" before showing the
full rsvp form (Issue 881).
"""

import pytest
from community.models import EventRSVP, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event
from tests.conftest import future_iso

URL_TEMPLATE = "/api/community/public/events/{event_id}/rsvp-phone-check/"


def url(event):
    return URL_TEMPLATE.format(event_id=event.id)


def post(api_client, event, phone_number="+14155550123"):
    return api_client.post(
        url(event), {"phone_number": phone_number}, content_type="application/json"
    )


@pytest.fixture
def official_event(db):
    return make_official_event()


@pytest.mark.django_db
class TestPublicRsvpPhoneCheck:
    def test_unknown_phone_is_new(self, api_client, official_event):
        response = post(api_client, official_event)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "new"
        assert "rsvp_token" not in body

    def test_member_phone_returns_member(self, api_client, official_event, test_user):
        response = post(api_client, official_event, phone_number=test_user.phone_number)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "member"
        assert "rsvp_token" not in body

    def test_non_member_without_rsvp_returns_non_member(self, api_client, official_event):
        make_non_member("+14155550199", "guest@example.com")

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        assert response.json()["status"] == "non_member"

    def test_non_member_already_rsvpd_returns_non_member_no_token(
        self, api_client, official_event, fake_email_sender
    ):
        guest = make_non_member("+14155550199", "guest@example.com")
        EventRSVP.objects.create(event=official_event, user=guest, status=RSVPStatus.ATTENDING)

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "non_member"
        assert "rsvp_token" not in body

    def test_non_member_with_email_always_gets_manage_link(
        self, api_client, official_event, fake_email_sender
    ):
        guest = make_non_member("+14155550199", "guest@example.com")

        post(api_client, official_event, phone_number="+14155550199")

        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "guest@example.com"
        token = NonMemberRsvpToken.objects.get(user=guest)
        assert token.token in sent["text"]

    def test_non_member_repeated_probe_does_not_resend_within_cooldown(
        self, api_client, official_event, fake_email_sender
    ):
        guest = make_non_member("+14155550199", "guest@example.com")

        post(api_client, official_event, phone_number="+14155550199")
        token_after_first = NonMemberRsvpToken.objects.get(user=guest)
        original_expires_at = token_after_first.expires_at

        post(api_client, official_event, phone_number="+14155550199")

        fake_email_sender.send.assert_called_once()
        token_after_first.refresh_from_db()
        assert token_after_first.expires_at == original_expires_at

    def test_non_member_without_email_sends_no_email(
        self, api_client, official_event, fake_email_sender
    ):
        make_non_member("+14155550199", "")

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        assert response.json()["status"] == "non_member"
        fake_email_sender.send.assert_not_called()

    def test_invalid_phone_is_new(self, api_client, official_event):
        response = post(api_client, official_event, phone_number="not-a-phone")

        assert response.status_code == 200
        assert response.json()["status"] == "new"

    def test_nonexistent_event_returns_404(self, api_client):
        response = api_client.post(
            "/api/community/public/events/00000000-0000-0000-0000-000000000000/rsvp-phone-check/",
            {"phone_number": "+14155550123"},
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_non_member_response_hides_attendance(self, api_client, fake_email_sender):
        this_event = make_official_event()
        other_event = make_official_event(title="Other Event", start_datetime=future_iso(days=45))
        rsvpd_here = make_non_member("+14155550111", "here@example.com")
        rsvpd_elsewhere = make_non_member("+14155550222", "elsewhere@example.com")
        never_rsvpd = make_non_member("+14155550333", "never@example.com")
        EventRSVP.objects.create(event=this_event, user=rsvpd_here, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(
            event=other_event, user=rsvpd_elsewhere, status=RSVPStatus.ATTENDING
        )

        bodies = [
            post(api_client, this_event, phone_number=u.phone_number).json()
            for u in (rsvpd_here, rsvpd_elsewhere, never_rsvpd)
        ]

        assert bodies == [{"status": "non_member"}] * 3
