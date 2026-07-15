"""GET /events/{id}/ with a non-member RSVP token — unlocks member-only fields
on any public-RSVP-eligible event for a valid token holder (issue #873)."""

import pytest
from community.models import Event, EventRSVP, EventType, PageVisibility, RSVPStatus
from users.models import NonMemberRsvpToken, User

from tests.conftest import future_iso


@pytest.fixture
def official_event(db, test_user):
    return Event.objects.create(
        title="Public Official Event",
        start_datetime=future_iso(days=20),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        rsvp_enabled=True,
        whatsapp_link="https://chat.whatsapp.com/abc123",
        created_by=test_user,
    )


@pytest.fixture
def other_event(db, test_user):
    return Event.objects.create(
        title="Other Event",
        start_datetime=future_iso(days=21),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def non_member(db):
    user = User.objects.create_user(
        phone_number="+12025550188",
        first_name="Non",
        last_name="Member",
        email="rsvp@example.com",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
class TestGetEventWithToken:
    def test_no_token_stays_locked(self, api_client, official_event):
        response = api_client.get(f"/api/community/events/{official_event.id}/")
        assert response.status_code == 200, response.content
        assert response.json()["whatsapp_link"] == ""

    def test_valid_scoped_token_unlocks_links(self, api_client, official_event, non_member):
        EventRSVP.objects.create(event=official_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        assert response.status_code == 200, response.content
        assert response.json()["whatsapp_link"] == "https://chat.whatsapp.com/abc123"

    def test_token_from_other_event_unlocks_eligible_event(
        self, api_client, official_event, other_event, non_member
    ):
        # One token, reused across events: RSVP'd to other_event, no RSVP on
        # official_event, but the token still unlocks it (issue #873).
        EventRSVP.objects.create(event=other_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        assert response.status_code == 200, response.content
        assert response.json()["whatsapp_link"] == "https://chat.whatsapp.com/abc123"

    def test_token_does_not_unlock_members_only_event(self, api_client, official_event, non_member):
        official_event.visibility = PageVisibility.MEMBERS_ONLY
        official_event.save(update_fields=["visibility"])
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        # Members-only events never accept public RSVPs — a token can't unlock them.
        assert response.status_code == 404, response.content

    def test_token_never_unlocks_invited_list(self, api_client, official_event, non_member):
        invited = User.objects.create_user(
            phone_number="+12025550199", first_name="Invited", last_name="Member"
        )
        official_event.invited_users.add(invited)
        EventRSVP.objects.create(event=official_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        body = response.json()
        assert body["invited_user_ids"] == []
        assert str(invited.id) not in body["invited_user_ids"]

    def test_valid_token_reports_own_viewer_user_id(self, api_client, official_event, non_member):
        EventRSVP.objects.create(event=official_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        assert response.status_code == 200, response.content
        assert response.json()["viewer_user_id"] == str(non_member.id)

    def test_no_token_reports_no_viewer_user_id(self, api_client, official_event):
        response = api_client.get(f"/api/community/events/{official_event.id}/")
        assert response.status_code == 200, response.content
        assert response.json()["viewer_user_id"] is None
