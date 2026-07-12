import pytest
from community.models import Event, EventRSVP, RSVPStatus
from users.models import User

from tests._public_rsvp_helpers import make_non_member
from tests.conftest import future_iso


def _one_spot_event(creator):
    return Event.objects.create(
        title="One Spot",
        start_datetime=future_iso(days=30),
        rsvp_enabled=True,
        max_attendees=1,
        created_by=creator,
    )


def _rsvp(api_client, event, headers, status=RSVPStatus.ATTENDING):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": status},
        content_type="application/json",
        **headers,
    )


def _promoted_email_count(fake_email_sender, to):
    return sum(
        1
        for c in fake_email_sender.send.call_args_list
        if c.kwargs["to"] == to and "off the waitlist" in c.kwargs["subject"]
    )


@pytest.mark.django_db
class TestWaitlistPromotionEmailsNonMember:
    def test_member_delete_emails_promoted_non_member(
        self, api_client, test_user, auth_headers, fake_email_sender
    ):
        event = _one_spot_event(test_user)
        _rsvp(api_client, event, auth_headers)  # member takes the only spot
        waited = make_non_member("+14155559911", "waited@e.com", name="Waited")
        EventRSVP.objects.create(event=event, user=waited, status=RSVPStatus.WAITLISTED)

        api_client.delete(f"/api/community/events/{event.id}/rsvp/", **auth_headers)

        assert EventRSVP.objects.get(event=event, user=waited).status == RSVPStatus.ATTENDING
        assert _promoted_email_count(fake_email_sender, "waited@e.com") == 1

    def test_member_status_change_emails_promoted_non_member(
        self, api_client, test_user, auth_headers, fake_email_sender
    ):
        event = _one_spot_event(test_user)
        _rsvp(api_client, event, auth_headers)
        waited = make_non_member("+14155559912", "waited2@e.com", name="Waited Two")
        EventRSVP.objects.create(event=event, user=waited, status=RSVPStatus.WAITLISTED)

        _rsvp(api_client, event, auth_headers, status=RSVPStatus.CANT_GO)  # frees the spot

        assert EventRSVP.objects.get(event=event, user=waited).status == RSVPStatus.ATTENDING
        assert _promoted_email_count(fake_email_sender, "waited2@e.com") == 1

    def test_promoted_member_is_not_emailed(
        self, api_client, test_user, auth_headers, fake_email_sender
    ):
        event = _one_spot_event(test_user)
        _rsvp(api_client, event, auth_headers)
        member = User.objects.create_user(
            phone_number="+14155559913", password="p", email="member@e.com"
        )
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.WAITLISTED)

        api_client.delete(f"/api/community/events/{event.id}/rsvp/", **auth_headers)

        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.ATTENDING
        assert _promoted_email_count(fake_email_sender, "member@e.com") == 0
