import pytest
from community.models import EventRSVP, EventType, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event

GET_URL = "/api/community/public/my-rsvps/"


@pytest.fixture
def nonmember(db):
    return make_non_member("+14155550001", "nm@example.com", name="non member")


@pytest.fixture
def official_event(db):
    return make_official_event(title="Official A")


@pytest.mark.django_db
class TestGetMyRsvps:
    def test_valid_token_returns_rsvps(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["display_name"] == "non member"
        assert len(body["rsvps"]) == 1
        assert body["rsvps"][0]["status"] == RSVPStatus.ATTENDING
        assert body["rsvps"][0]["event"]["id"] == str(official_event.id)

    def test_only_official_events_appear(self, api_client, nonmember, official_event):
        community_event = make_official_event(title="Community B", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        ids = {r["event"]["id"] for r in resp.json()["rsvps"]}
        assert ids == {str(official_event.id)}

    def test_missing_token_404(self, api_client):
        assert api_client.get(GET_URL).status_code == 404

    def test_unknown_token_404(self, api_client):
        assert api_client.get(f"{GET_URL}?token=nope").status_code == 404

    def test_revoked_token_404(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        token.revoke()
        assert api_client.get(f"{GET_URL}?token={token.token}").status_code == 404
