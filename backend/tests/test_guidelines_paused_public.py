import pytest
from community.events.viewer import resolve_event_viewer
from community.models import EventRSVP, JoinRequest, RSVPStatus
from community.validation import Code
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import first_code, make_non_member, make_official_event, post

PHONE = "+14155550123"
EMAIL = "sam@example.com"


@pytest.fixture
def paused(db):
    user = make_non_member(PHONE, EMAIL)
    user.is_paused = True
    user.save(update_fields=["is_paused"])
    return user


@pytest.fixture
def official_event(db):
    return make_official_event()


@pytest.mark.django_db
class TestPausedPublicRsvp:
    def test_phone_check_answers_non_member_without_emailing(
        self, api_client, official_event, paused, fake_email_sender
    ):
        response = api_client.post(
            f"/api/community/public/events/{official_event.id}/rsvp-phone-check/",
            {"phone_number": PHONE},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "non_member"
        fake_email_sender.send.assert_not_called()
        assert not NonMemberRsvpToken.objects.filter(user=paused).exists()

    def test_submit_gets_generic_rejection(
        self, api_client, official_event, paused, fake_email_sender
    ):
        response = post(api_client, official_event)

        assert response.status_code == 409
        assert first_code(response) == Code.Event.RSVP_COULD_NOT_BE_CREATED
        assert not EventRSVP.objects.filter(user=paused).exists()
        fake_email_sender.send.assert_not_called()

    def test_resend_sends_nothing(self, api_client, paused, fake_email_sender):
        response = api_client.post(
            "/api/community/public/my-rsvps/resend/",
            {"phone_number": PHONE},
            content_type="application/json",
        )

        assert response.status_code == 200
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestPausedRsvpToken:
    @pytest.fixture
    def token(self, paused):
        return NonMemberRsvpToken.issue_or_extend(paused).token

    def test_resolve_user_returns_none(self, token):
        assert NonMemberRsvpToken.resolve_user(token) is None

    def test_viewer_falls_back_to_anonymous(self, rf, official_event, token):
        request = rf.get(f"/api/community/events/x/?token={token}")
        request.auth = None

        assert resolve_event_viewer(request, official_event.id) is None

    def test_manage_list_404s(self, api_client, token):
        response = api_client.get(f"/api/community/public/my-rsvps/?token={token}")

        assert response.status_code == 404

    def test_manage_update_404s(self, api_client, official_event, paused, token):
        response = api_client.post(
            f"/api/community/public/my-rsvps/{official_event.id}/?token={token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )

        assert response.status_code == 404
        assert not EventRSVP.objects.filter(user=paused).exists()


@pytest.mark.django_db
class TestPausedJoinRequest:
    def _submit(self, api_client, **overrides):
        body = {
            "first_name": "Sam",
            "last_name": "Green",
            "phone_number": PHONE,
            "email": EMAIL,
            "sms_consent": True,
            "guidelines_consent": True,
            **overrides,
        }
        return api_client.post(
            "/api/community/join-request/", body, content_type="application/json"
        )

    @pytest.mark.parametrize(
        "overrides", [{"email": "other@example.com"}, {"phone_number": "+14155550999"}]
    )
    def test_match_gets_decoy_without_persisting(self, api_client, paused, overrides):
        response = self._submit(api_client, **overrides)

        assert response.status_code == 201
        assert response.json()["id"] == ""
        assert not JoinRequest.objects.exists()
