import pytest
from community._validation import Code
from community.models import (
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventType,
    PageVisibility,
    RsvpQuestionType,
    RSVPStatus,
)
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso

EVENTS_URL = "/api/community/events/"
PAID = {"price": "$10", "venmo_link": "https://venmo.com/x"}


def _auth(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def host(db) -> User:
    user = User.objects.create_user(phone_number="+12025556100", password="x", first_name="Host")
    role = Role.objects.create(
        name="auto_rsvp_tagger",
        permissions=[PermissionKey.TAG_OFFICIAL_EVENT, PermissionKey.TAG_CLUB_EVENT],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def invitee(db) -> User:
    return User.objects.create_user(phone_number="+12025556101", password="x", first_name="Co")


@pytest.fixture
def guest(db) -> User:
    return User.objects.create_user(phone_number="+12025556102", password="x", first_name="Guest")


def _create(api_client, host: User, event_type: str, **overrides) -> Event:
    payload = {
        "title": "Auto RSVP",
        "start_datetime": future_iso(days=14),
        "end_datetime": future_iso(days=14, hours=2),
        "event_type": event_type,
        "visibility": PageVisibility.PUBLIC,
        "rsvp_enabled": True,
        **overrides,
    }
    response = api_client.post(EVENTS_URL, payload, content_type="application/json", **_auth(host))
    assert response.status_code == 201, response.content
    return Event.objects.get(id=response.json()["id"])


def _accept(api_client, event: Event, user: User):
    invite = EventCoHostInvite.objects.get(event=event, user=user)
    return api_client.post(
        f"{EVENTS_URL}{event.id}/cohost-invites/{invite.id}/accept/",
        content_type="application/json",
        **_auth(user),
    )


def _rsvp_status(event: Event, user: User) -> str | None:
    return EventRSVP.objects.filter(event=event, user=user).values_list("status", flat=True).first()


@pytest.mark.django_db
class TestAutoRsvpOnCreate:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_host_is_attending(self, api_client, host, event_type, fake_email_sender):
        event = _create(api_client, host, event_type)
        assert _rsvp_status(event, host) == RSVPStatus.ATTENDING
        fake_email_sender.send.assert_not_called()
        assert not Notification.objects.filter(
            notification_type=NotificationType.RSVP_STATUS_CHANGED
        ).exists()

    def test_response_shows_host_going(self, api_client, host):
        response = api_client.post(
            EVENTS_URL,
            {
                "title": "Auto RSVP",
                "start_datetime": future_iso(days=14),
                "event_type": EventType.OFFICIAL,
                "visibility": PageVisibility.PUBLIC,
                "rsvp_enabled": True,
            },
            content_type="application/json",
            **_auth(host),
        )
        assert response.status_code == 201
        assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING

    def test_community_event_has_no_auto_rsvp(self, api_client, host):
        event = _create(api_client, host, EventType.COMMUNITY)
        assert not EventRSVP.objects.filter(event=event).exists()

    def test_rsvps_disabled_skips(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL, rsvp_enabled=False)
        assert not EventRSVP.objects.filter(event=event).exists()

    def test_payment_gated_event_rsvps_host_without_payment(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL, **PAID)
        rsvp = EventRSVP.objects.get(event=event, user=host)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.paid_confirmed_at is None

    def test_payment_gate_still_applies_to_members(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL, **PAID)
        member = User.objects.create_user(phone_number="+12025556102", password="x")
        response = api_client.post(
            f"{EVENTS_URL}{event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **_auth(member),
        )
        assert_error_code(response, Code.Event.PAYMENT_CONFIRMATION_REQUIRED)
        assert _rsvp_status(event, member) is None

    def test_required_question_rsvps_host_without_answers(self, api_client, host):
        event = _create(
            api_client,
            host,
            EventType.CLUB,
            rsvp_questions=[
                {"label": "diet?", "field_type": RsvpQuestionType.TEXTAREA, "required": True}
            ],
        )
        rsvp = EventRSVP.objects.get(event=event, user=host)
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.questionnaire_responses == {}

    def test_draft_official_event_rsvps_host(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL, status="draft")
        assert _rsvp_status(event, host) == RSVPStatus.ATTENDING


def _patch(api_client, event: Event, user: User, payload: dict):
    response = api_client.patch(
        f"{EVENTS_URL}{event.id}/", payload, content_type="application/json", **_auth(user)
    )
    assert response.status_code == 200, response.content
    return response


@pytest.mark.django_db
class TestAutoRsvpOnTypeSwitch:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_switching_rsvps_all_hosts(self, api_client, host, event_type, fake_email_sender):
        event = _create(api_client, host, EventType.COMMUNITY)
        co_host = User.objects.create_user(phone_number="+12025556101", password="x")
        event.co_hosts.add(co_host)
        response = _patch(api_client, event, host, {"event_type": event_type})
        assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING
        assert _rsvp_status(event, host) == RSVPStatus.ATTENDING
        assert _rsvp_status(event, co_host) == RSVPStatus.ATTENDING
        fake_email_sender.send.assert_not_called()

    def test_switching_keeps_existing_rsvp(self, api_client, host):
        event = _create(api_client, host, EventType.COMMUNITY)
        EventRSVP.objects.create(event=event, user=host, status=RSVPStatus.MAYBE)
        _patch(api_client, event, host, {"event_type": EventType.OFFICIAL})
        assert _rsvp_status(event, host) == RSVPStatus.MAYBE

    def test_switching_between_official_and_club_does_not_re_rsvp(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL)
        api_client.delete(f"{EVENTS_URL}{event.id}/rsvp/", **_auth(host))
        _patch(api_client, event, host, {"event_type": EventType.CLUB})
        assert _rsvp_status(event, host) is None

    def test_other_edits_do_not_re_rsvp(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL)
        api_client.delete(f"{EVENTS_URL}{event.id}/rsvp/", **_auth(host))
        _patch(api_client, event, host, {"title": "renamed"})
        assert _rsvp_status(event, host) is None

    def test_community_edit_does_not_rsvp(self, api_client, host):
        event = _create(api_client, host, EventType.COMMUNITY)
        _patch(api_client, event, host, {"title": "renamed"})
        assert not EventRSVP.objects.filter(event=event).exists()


@pytest.mark.django_db
class TestHostCanChangeAutoRsvp:
    def test_host_can_withdraw(self, api_client, host):
        event = _create(api_client, host, EventType.OFFICIAL)
        response = api_client.delete(f"{EVENTS_URL}{event.id}/rsvp/", **_auth(host))
        assert response.status_code == 204
        assert _rsvp_status(event, host) is None

    def test_host_can_mark_cant_go(self, api_client, host):
        event = _create(api_client, host, EventType.CLUB)
        response = api_client.post(
            f"{EVENTS_URL}{event.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO},
            content_type="application/json",
            **_auth(host),
        )
        assert response.status_code == 200
        assert _rsvp_status(event, host) == RSVPStatus.CANT_GO


@pytest.mark.django_db
class TestAutoRsvpOnCohostAccept:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_accepting_cohost_is_attending(
        self, api_client, host, invitee, event_type, fake_email_sender
    ):
        event = _create(api_client, host, event_type, co_host_ids=[str(invitee.pk)])
        assert _rsvp_status(event, invitee) is None
        fake_email_sender.send.reset_mock()

        response = _accept(api_client, event, invitee)

        assert response.status_code == 200
        assert _rsvp_status(event, invitee) == RSVPStatus.ATTENDING
        fake_email_sender.send.assert_not_called()
        assert not Notification.objects.filter(
            notification_type=NotificationType.RSVP_STATUS_CHANGED
        ).exists()

    def test_community_event_accept_has_no_auto_rsvp(self, api_client, host, invitee):
        event = _create(api_client, host, EventType.COMMUNITY, co_host_ids=[str(invitee.pk)])
        response = _accept(api_client, event, invitee)
        assert response.status_code == 200
        assert _rsvp_status(event, invitee) is None

    @pytest.mark.parametrize("prior", [RSVPStatus.CANT_GO, RSVPStatus.MAYBE])
    def test_existing_rsvp_is_not_overwritten(self, api_client, host, invitee, prior):
        event = _create(api_client, host, EventType.OFFICIAL, co_host_ids=[str(invitee.pk)])
        EventRSVP.objects.create(event=event, user=invitee, status=prior)

        response = _accept(api_client, event, invitee)

        assert response.status_code == 200
        assert _rsvp_status(event, invitee) == prior

    def test_full_event_waitlists_accepting_cohost(self, api_client, host, invitee, guest):
        event = _create(
            api_client, host, EventType.OFFICIAL, max_attendees=2, co_host_ids=[str(invitee.pk)]
        )
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)

        response = _accept(api_client, event, invitee)

        assert response.status_code == 200
        assert _rsvp_status(event, invitee) == RSVPStatus.WAITLISTED
