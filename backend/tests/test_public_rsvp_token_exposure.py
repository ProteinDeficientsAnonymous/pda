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
        body = post(api_client, official_event).json()
        assert "rsvp_token" in body

    def test_phone_match_returns_a_token_scoped_to_the_existing_row(
        self, api_client, official_event, fake_email_sender
    ):
        existing = make_non_member("+14155550123", "old@example.com")

        body = post(api_client, official_event, email="attacker@example.com").json()

        returned = body["rsvp_token"]
        assert returned
        assert NonMemberRsvpToken.resolve_user(returned) == existing

    def test_email_only_match_hands_back_a_token_for_a_row_the_caller_may_not_own(
        self, api_client, official_event, fake_email_sender
    ):
        # issue 1029: fresh phone + victim's email → token bound to the victim, no proof of ownership
        victim = make_non_member("+14155550999", "victim@example.com", name="Victim Person")

        body = post(
            api_client,
            official_event,
            phone_number="+14155550123",
            email="victim@example.com",
        ).json()

        returned = body["rsvp_token"]
        assert returned
        assert NonMemberRsvpToken.resolve_user(returned) == victim
        assert EventRSVP.objects.filter(event=official_event, user=victim).exists()

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
