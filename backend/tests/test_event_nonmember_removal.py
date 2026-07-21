"""Issue 1022: removing non-member RSVPs when an event loses public-RSVP eligibility."""

import pytest
from community._validation import Code
from community.models import EventRSVP, EventType, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._public_rsvp_helpers import make_non_member, make_official_event


@pytest.fixture
def manage_events_user(db):
    user = User.objects.create_user(
        phone_number="+14155551234",
        password="eventmanagerpass123",
        first_name="Event",
        last_name="Manager",
    )
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def manage_events_headers(manage_events_user):
    refresh = RefreshToken.for_user(manage_events_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _patch_official_off(api_client, event, headers, **extra):
    return api_client.patch(
        f"/api/community/events/{event.id}/",
        {"event_type": EventType.COMMUNITY, **extra},
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestNonMemberRemovalOnIneligibleEvent:
    @pytest.mark.parametrize(
        "status",
        [RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED, RSVPStatus.MAYBE, RSVPStatus.CANT_GO],
    )
    def test_force_removes_non_member_of_any_status(
        self, api_client, manage_events_headers, fake_email_sender, status
    ):
        event = make_official_event()
        non_member = make_non_member("+14155559001", "removed@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=status)

        response = _patch_official_off(api_client, event, manage_events_headers, force=True)

        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=event, user=non_member)
        assert rsvp.status == RSVPStatus.REMOVED

    def test_without_force_rejected_with_count_and_no_changes(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        event = make_official_event()
        make_non_member("+14155559002", "one@e.com")
        make_non_member("+14155559003", "two@e.com")
        for phone, email in [("+14155559002", "one@e.com"), ("+14155559003", "two@e.com")]:
            EventRSVP.objects.create(
                event=event, user=User.objects.get(email=email), status=RSVPStatus.ATTENDING
            )

        response = _patch_official_off(api_client, event, manage_events_headers)

        assert response.status_code == 409
        assert_error_code(response, Code.Event.WOULD_REMOVE_NON_MEMBERS)
        assert response.json()["detail"][0]["params"]["count"] == 2
        event.refresh_from_db()
        assert event.event_type == EventType.OFFICIAL

    def test_member_rsvps_untouched(
        self, api_client, manage_events_headers, fake_email_sender, test_user
    ):
        event = make_official_event()
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
        non_member = make_non_member("+14155559004", "nm@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = _patch_official_off(api_client, event, manage_events_headers, force=True)

        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=test_user).status == RSVPStatus.ATTENDING
        assert EventRSVP.objects.get(event=event, user=non_member).status == RSVPStatus.REMOVED

    def test_removal_sends_best_effort_email(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        event = make_official_event()
        non_member = make_non_member("+14155559005", "emailme@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = _patch_official_off(api_client, event, manage_events_headers, force=True)

        assert response.status_code == 200
        calls = [
            c for c in fake_email_sender.send.call_args_list if c.kwargs["to"] == "emailme@e.com"
        ]
        assert len(calls) == 1
        assert "removed" in calls[0].kwargs["subject"]

    def test_email_failure_does_not_roll_back_removal(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        from notifications.email_sender import SendResult

        fake_email_sender.send.return_value = SendResult(success=False, error="boom")
        event = make_official_event()
        non_member = make_non_member("+14155559006", "failmail@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = _patch_official_off(api_client, event, manage_events_headers, force=True)

        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=non_member).status == RSVPStatus.REMOVED

    def test_edit_that_stays_eligible_never_triggers_check(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        event = make_official_event()
        non_member = make_non_member("+14155559007", "stays@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"title": "Still official, still eligible"},
            content_type="application/json",
            **manage_events_headers,
        )

        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=non_member).status == RSVPStatus.ATTENDING

    def test_edit_on_already_ineligible_event_never_triggers_check(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        event = make_official_event(event_type=EventType.COMMUNITY)
        non_member = make_non_member("+14155559008", "already@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"title": "Already ineligible, no-op check"},
            content_type="application/json",
            **manage_events_headers,
        )

        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=non_member).status == RSVPStatus.ATTENDING

    def test_cancelling_event_does_not_trigger_removal(
        self, api_client, manage_events_headers, fake_email_sender
    ):
        """Cancelling also flips is_public_rsvp_eligible false, but it has its own
        attendee-cancellation notification — the removal check must not double-fire."""
        event = make_official_event()
        non_member = make_non_member("+14155559009", "cancelled@e.com")
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)

        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"status": "cancelled"},
            content_type="application/json",
            **manage_events_headers,
        )

        assert response.status_code == 200
        assert EventRSVP.objects.get(event=event, user=non_member).status == RSVPStatus.ATTENDING
