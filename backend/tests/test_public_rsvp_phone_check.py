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
        assert body["rsvp_token"] == ""

    def test_member_phone_returns_member(self, api_client, official_event, test_user):
        response = post(api_client, official_event, phone_number=test_user.phone_number)

        assert response.status_code == 200
        assert response.json()["status"] == "member"

    def test_non_member_without_rsvp_is_new(self, api_client, official_event):
        make_non_member("+14155550199", "guest@example.com")

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "new"
        assert body["rsvp_token"] == ""

    def test_non_member_already_rsvpd_returns_token(self, api_client, official_event):
        guest = make_non_member("+14155550199", "guest@example.com")
        EventRSVP.objects.create(event=official_event, user=guest, status=RSVPStatus.ATTENDING)

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "already_rsvpd"
        assert body["rsvp_token"] != ""
        assert NonMemberRsvpToken.resolve_user(body["rsvp_token"]) == guest

    def test_already_rsvpd_on_other_event_is_recognized_for_this_one(
        self, api_client, official_event, fake_email_sender
    ):
        guest = make_non_member("+14155550199", "guest@example.com")
        other_event = make_official_event(title="Other Event", start_datetime=future_iso(days=45))
        EventRSVP.objects.create(event=other_event, user=guest, status=RSVPStatus.ATTENDING)

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "recognized"
        assert body["rsvp_token"] == ""

    def test_recognized_sends_login_link_email(self, api_client, official_event, fake_email_sender):
        guest = make_non_member("+14155550199", "guest@example.com")
        other_event = make_official_event(title="Other Event", start_datetime=future_iso(days=45))
        EventRSVP.objects.create(event=other_event, user=guest, status=RSVPStatus.ATTENDING)

        post(api_client, official_event, phone_number="+14155550199")

        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "guest@example.com"
        token = NonMemberRsvpToken.objects.get(user=guest)
        assert token.token in sent["text"]

    def test_recognized_without_email_falls_back_to_new(
        self, api_client, official_event, fake_email_sender
    ):
        guest = make_non_member("+14155550199", "")
        other_event = make_official_event(title="Other Event", start_datetime=future_iso(days=45))
        EventRSVP.objects.create(event=other_event, user=guest, status=RSVPStatus.ATTENDING)

        response = post(api_client, official_event, phone_number="+14155550199")

        assert response.status_code == 200
        assert response.json()["status"] == "new"
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
