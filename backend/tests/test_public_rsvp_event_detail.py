"""GET /events/{id}/ with a non-member RSVP token — unlocks member-only fields
scoped to the one event the token holder RSVP'd to."""

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

    def test_token_scoped_to_other_event_does_not_unlock(
        self, api_client, official_event, other_event, non_member
    ):
        EventRSVP.objects.create(event=other_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        assert response.status_code == 200, response.content
        assert response.json()["whatsapp_link"] == ""

    def test_token_never_unlocks_invited_list(self, api_client, official_event, non_member):
        EventRSVP.objects.create(event=official_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        response = api_client.get(
            f"/api/community/events/{official_event.id}/", {"token": token.token}
        )
        body = response.json()
        assert body["invited_user_ids"] == []
