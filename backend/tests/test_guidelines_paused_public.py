import pytest
from audit.models import AuditLogEntry
from community.events.viewer import resolve_event_viewer
from community.models import EventRSVP, JoinFormQuestion, JoinRequest, RSVPStatus
from community.validation import Code
from users.models import MembershipStatus, PublicRsvpToken, User

from tests._public_rsvp_helpers import first_code, make_official_event, make_public_rsvper, post
from tests._users import make_user

PHONE = "+14155550123"
EMAIL = "sam@example.com"


@pytest.fixture
def paused(db):
    user = make_public_rsvper(PHONE, EMAIL)
    user.is_paused = True
    user.save(update_fields=["is_paused"])
    return user


@pytest.fixture
def official_event(db):
    return make_official_event()


@pytest.mark.django_db
class TestPausedPublicRsvp:
    def test_phone_check_routes_to_login_without_emailing(
        self, api_client, official_event, paused, fake_email_sender
    ):
        response = api_client.post(
            f"/api/community/public/events/{official_event.id}/rsvp-phone-check/",
            {"phone_number": PHONE},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == "member"
        fake_email_sender.send.assert_not_called()
        assert not PublicRsvpToken.objects.filter(user=paused).exists()

    def test_submit_gets_generic_rejection(
        self,
        api_client,
        official_event,
        paused,
        fake_email_sender,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = post(api_client, official_event)

        assert response.status_code == 409
        assert first_code(response) == Code.Event.RSVP_COULD_NOT_BE_CREATED
        assert AuditLogEntry.objects.filter(action="public_rsvp_paused_user_blocked").exists()
        assert not EventRSVP.objects.filter(user=paused).exists()
        fake_email_sender.send.assert_not_called()

    def test_submit_from_paused_member_is_told_to_sign_in(self, api_client, official_event):
        member = make_user(phone_number=PHONE, email=EMAIL, is_paused=True)
        User.objects.filter(pk=member.pk).update(
            membership_status=MembershipStatus.GUIDELINES_PAUSED
        )

        response = post(api_client, official_event)

        assert response.status_code == 409
        assert first_code(response) == Code.Event.MEMBER_CONTACT_MUST_SIGN_IN

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
        return PublicRsvpToken.issue_or_extend(paused).token

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
            "answers": {str(q.id): "x" for q in JoinFormQuestion.objects.filter(required=True)},
            **overrides,
        }
        return api_client.post(
            "/api/community/join-request/", body, content_type="application/json"
        )

    @pytest.mark.parametrize(
        "overrides", [{"email": "other@example.com"}, {"phone_number": "+14155550999"}]
    )
    def test_match_is_told_to_sign_in(self, api_client, paused, overrides):
        response = self._submit(api_client, **overrides)

        assert response.status_code == 409
        assert first_code(response) == Code.JoinRequest.ALREADY_MEMBER
        assert not JoinRequest.objects.exists()
