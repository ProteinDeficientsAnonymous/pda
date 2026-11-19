"""Tests for payment-link and payment-status visibility in the event serializers."""

import pytest
from community.models import Event, EventType

from tests._payment_helpers import create_paid_event
from tests._public_rsvp_helpers import make_official_event


def _paid_event(creator, **overrides) -> Event:
    return create_paid_event(created_by=creator, **overrides)


@pytest.fixture
def paid_public_event(db):
    return make_official_event(
        title="Paid Official Event",
        price="$10",
        venmo_link="https://venmo.com/u/host",
    )


@pytest.mark.django_db
class TestPublicPaymentLinkVisibility:
    def _get(self, api_client, event):
        return api_client.get(f"/api/community/events/{event.id}/")

    def test_anon_sees_payment_links_on_public_rsvp_eligible_event(
        self, api_client, paid_public_event
    ):
        response = self._get(api_client, paid_public_event)
        assert response.status_code == 200
        body = response.json()
        assert body["venmo_link"] == "https://venmo.com/u/host"
        assert body["price"] == "$10"

    def test_anon_does_not_see_payment_links_on_non_eligible_event(
        self, api_client, paid_public_event
    ):
        paid_public_event.rsvp_enabled = False
        paid_public_event.save(update_fields=["rsvp_enabled"])
        response = self._get(api_client, paid_public_event)
        assert response.status_code == 200
        assert response.json()["venmo_link"] == ""

    def test_anon_does_not_see_payment_links_on_community_event(
        self, api_client, paid_public_event
    ):
        paid_public_event.event_type = EventType.COMMUNITY
        paid_public_event.save(update_fields=["event_type"])
        response = self._get(api_client, paid_public_event)
        assert response.status_code == 200
        assert response.json()["venmo_link"] == ""

    def test_anon_still_does_not_see_other_member_only_links(self, api_client, paid_public_event):
        paid_public_event.whatsapp_link = "https://chat.whatsapp.com/abc"
        paid_public_event.save(update_fields=["whatsapp_link"])
        response = self._get(api_client, paid_public_event)
        assert response.json()["whatsapp_link"] == ""

    def test_member_still_sees_payment_links_on_non_eligible_event(
        self, api_client, paid_public_event, auth_headers
    ):
        paid_public_event.rsvp_enabled = False
        paid_public_event.save(update_fields=["rsvp_enabled"])
        response = api_client.get(f"/api/community/events/{paid_public_event.id}/", **auth_headers)
        assert response.json()["venmo_link"] == "https://venmo.com/u/host"


@pytest.mark.django_db
class TestPaymentLinkVisibility:
    def _venmo(self, api_client, event, **headers):
        return api_client.get(f"/api/community/events/{event.id}/", **headers).json()["venmo_link"]

    def test_anon_sees_payment_links_on_an_eligible_event(self, api_client, test_user):
        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        assert self._venmo(api_client, event) == "https://venmo.com/u/host"

    def test_anon_does_not_see_them_on_an_ineligible_event(self, api_client, test_user):
        event = _paid_event(test_user, event_type=EventType.COMMUNITY)
        assert self._venmo(api_client, event) == ""

    def test_member_always_sees_them(self, api_client, auth_headers, test_user):
        event = _paid_event(test_user)
        assert self._venmo(api_client, event, **auth_headers) == "https://venmo.com/u/host"
