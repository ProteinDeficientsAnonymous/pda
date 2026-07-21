import pytest
from community._validation import Code
from community.models import EventRSVP, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import first_code, make_non_member, make_official_event, post


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

    def test_new_submission_still_returns_a_token_directly(
        self, api_client, official_event, fake_email_sender
    ):
        body = post(api_client, official_event).json()

        returned = body["rsvp_token"]
        assert returned
        user = NonMemberRsvpToken.resolve_user(returned)
        assert user.phone_number == "+14155550123"

    def test_phone_match_withholds_the_token_and_emails_it_instead(
        self, api_client, official_event, fake_email_sender
    ):
        existing = make_non_member("+14155550123", "old@example.com")

        body = post(api_client, official_event, email="attacker@example.com").json()

        assert body["rsvp_token"] == ""
        token = NonMemberRsvpToken.objects.get(user=existing)
        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "old@example.com"
        assert token.token in sent["text"]

    def test_email_only_match_is_rejected_not_adopted(
        self, api_client, official_event, fake_email_sender
    ):
        victim = make_non_member("+14155550999", "victim@example.com", name="Victim Person")

        response = post(
            api_client,
            official_event,
            phone_number="+14155550123",
            email="victim@example.com",
        )

        assert response.status_code == 409
        assert first_code(response) == Code.Event.RSVP_COULD_NOT_BE_CREATED
        assert not EventRSVP.objects.filter(event=official_event, user=victim).exists()

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
