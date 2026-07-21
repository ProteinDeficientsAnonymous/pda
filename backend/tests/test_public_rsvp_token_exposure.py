"""Regression tests for manage-token exposure in the public RSVP submit response.

The submit endpoint (POST /api/community/public/events/{event_id}/rsvp/) backs each
RSVP with a NonMemberRsvpToken. The token is a scoped magic link granting read/write
over that user's RSVP identity via /public/my-rsvps/. Whether it may appear in the
HTTP response body — versus being delivered only by email to the address on file —
depends on whether the submitter proved control of the resolved account.

These tests pin the current behaviour so the account-takeover surface (issue 1029)
is visible and any change to it is deliberate. They assert on the exact response
key `rsvp_token` (the earlier happy-path test checked `"token" not in body`, which
never matches that key and so silently passed while the token was present).
"""

import pytest
from community.models import EventRSVP, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event, post


@pytest.fixture
def official_event(db):
    return make_official_event(
        location="123 Vegan Way", whatsapp_link="https://chat.whatsapp.com/abc123"
    )


def _manage(api_client, token: str):
    return api_client.get(f"/api/community/public/my-rsvps/?token={token}")


@pytest.mark.django_db
class TestSubmitTokenExposure:
    def test_body_carries_the_rsvp_token_key(self, api_client, official_event, fake_email_sender):
        # A brand-new submitter proved control of the phone they entered, so the
        # token in the body unlocks only their own just-created RSVP.
        body = post(api_client, official_event).json()
        assert "rsvp_token" in body

    def test_phone_match_returns_a_token_scoped_to_the_existing_row(
        self, api_client, official_event, fake_email_sender
    ):
        # An existing non-member matched by PHONE. Whoever submitted controls that
        # phone number, so scoping the token to the matched row is defensible —
        # but the token IS handed back in the body (issue 1029). Pin it.
        existing = make_non_member("+14155550123", "old@example.com")

        body = post(api_client, official_event, email="attacker@example.com").json()

        returned = body["rsvp_token"]
        assert returned  # non-empty token in the body today
        assert NonMemberRsvpToken.resolve_user(returned) == existing

    def test_email_only_match_hands_back_a_token_for_a_row_the_caller_may_not_own(
        self, api_client, official_event, fake_email_sender
    ):
        # THE takeover vector (issue 1029): the submitter supplies a fresh phone
        # they control plus a VICTIM'S email. phone_match is None, email_match is
        # the victim, and the body returns a live token bound to the victim — with
        # no proof the caller owns that email. This test documents the current
        # (vulnerable) behaviour; when 1029 is fixed, flip the assertions to expect
        # an empty rsvp_token and an emailed link instead.
        victim = make_non_member("+14155550999", "victim@example.com", name="Victim Person")

        body = post(
            api_client,
            official_event,
            phone_number="+14155550123",  # attacker's own fresh number
            email="victim@example.com",  # the victim's email
        ).json()

        returned = body["rsvp_token"]
        assert returned
        # The token resolves to the VICTIM, and the RSVP landed on the victim's row.
        assert NonMemberRsvpToken.resolve_user(returned) == victim
        assert EventRSVP.objects.filter(event=official_event, user=victim).exists()

        # And that token is a working credential over the victim's identity.
        manage = _manage(api_client, returned)
        assert manage.status_code == 200
        assert manage.json()["user"]["email"] == "victim@example.com"

    def test_returned_token_grants_manage_access(
        self, api_client, official_event, fake_email_sender
    ):
        body = post(api_client, official_event).json()
        manage = _manage(api_client, body["rsvp_token"])
        assert manage.status_code == 200
        assert manage.json()["user"]["phone_number"] == "+14155550123"
        assert any(
            r["event"]["id"] == str(official_event.id) and r["status"] == RSVPStatus.ATTENDING
            for r in manage.json()["rsvps"]
        )
