import pytest
from community.models import EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event

GET_URL = "/api/community/public/my-rsvps/"


def _post_url(event):
    return f"/api/community/public/my-rsvps/{event.id}/"


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


@pytest.mark.django_db
class TestPostMyRsvps:
    def test_update_changes_status(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["rsvp"]["status"] == RSVPStatus.ATTENDING
        rsvp = EventRSVP.objects.get(event=official_event, user=nonmember)
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_update_extends_token_keeping_same_string(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        old_expiry = token.expires_at
        token.expires_at = timezone.now() + timezone.timedelta(minutes=1)  # simulate near-expiry
        token.save(update_fields=["expires_at"])
        api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        token.refresh_from_db()
        assert token.expires_at > old_expiry - timezone.timedelta(days=1)
        # same token string still resolves
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200

    def test_invalid_status_400(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.WAITLISTED},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_ineligible_event_404(self, api_client, nonmember):
        community_event = make_official_event(title="C", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(community_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_bad_token_404(self, api_client, official_event):
        resp = api_client.post(
            f"{_post_url(official_event)}?token=nope",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDeleteMyRsvps:
    def test_delete_removes_rsvp(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        assert not EventRSVP.objects.filter(event=official_event, user=nonmember).exists()
        # subsequent GET no longer lists it
        listed = api_client.get(f"{GET_URL}?token={token.token}").json()["rsvps"]
        assert listed == []

    def test_delete_promotes_waitlist(self, api_client, nonmember, official_event):
        official_event.max_attendees = 1
        official_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        waiter = make_non_member("+14155550002", "w@example.com", name="waiter")
        EventRSVP.objects.create(event=official_event, user=waiter, status=RSVPStatus.WAITLISTED)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        waiter_rsvp = EventRSVP.objects.get(event=official_event, user=waiter)
        assert waiter_rsvp.status == RSVPStatus.ATTENDING

    def test_delete_no_rsvp_404(self, api_client, nonmember, official_event):
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 404

    def test_delete_bad_token_404(self, api_client, official_event):
        resp = api_client.delete(f"{_post_url(official_event)}?token=nope")
        assert resp.status_code == 404
