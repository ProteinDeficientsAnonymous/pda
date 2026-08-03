"""Tests for payment-link and payment-status visibility in the event serializers."""

import pytest
from community.models import Event, EventType
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests._payment_helpers import create_paid_event, set_payment_flag
from tests._public_rsvp_helpers import make_official_event


@pytest.fixture(autouse=True)
def _flag_on(db):
    set_payment_flag(True)


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
class TestListSerializerPaymentParity:
    def _list(self, api_client, **headers):
        return api_client.get("/api/community/events/", **headers).json()

    def _find(self, body, event):
        return next(item for item in body if item["id"] == str(event.id))

    def test_anon_sees_payment_links_in_list_for_eligible_event(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        row = self._find(self._list(api_client), event)
        assert row["venmo_link"] == "https://venmo.com/u/host"

    def test_list_and_detail_agree_for_anon(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        row = self._find(self._list(api_client), event)
        detail = api_client.get(f"/api/community/events/{event.id}/").json()
        assert row["venmo_link"] == detail["venmo_link"]

    def test_anon_does_not_see_payment_links_in_list_for_community_event(
        self, api_client, test_user
    ):
        from community.models import EventType

        event = _paid_event(test_user, event_type=EventType.COMMUNITY)
        row = self._find(self._list(api_client), event)
        assert row["venmo_link"] == ""

    def test_anon_still_does_not_see_other_links_in_list(self, api_client, test_user):
        from community.models import EventType

        event = _paid_event(
            test_user,
            event_type=EventType.OFFICIAL,
            whatsapp_link="https://chat.whatsapp.com/abc",
        )
        row = self._find(self._list(api_client), event)
        assert row["whatsapp_link"] == ""


@pytest.mark.django_db
class TestPaymentLinkVisibilityIgnoresTheGateFlag:
    """EVENT_PAYMENT_CONFIRMATION governs whether payment is enforced, not who
    may see the cost — visibility must be identical either way."""

    def _venmo(self, api_client, event, **headers):
        return api_client.get(f"/api/community/events/{event.id}/", **headers).json()["venmo_link"]

    @pytest.mark.parametrize("flag", [True, False])
    def test_anon_sees_payment_links_on_an_eligible_event(self, api_client, test_user, flag):
        set_payment_flag(flag)
        event = _paid_event(test_user, event_type=EventType.OFFICIAL)
        assert self._venmo(api_client, event) == "https://venmo.com/u/host"

    @pytest.mark.parametrize("flag", [True, False])
    def test_anon_does_not_see_them_on_an_ineligible_event(self, api_client, test_user, flag):
        set_payment_flag(flag)
        event = _paid_event(test_user, event_type=EventType.COMMUNITY)
        assert self._venmo(api_client, event) == ""

    @pytest.mark.parametrize("flag", [True, False])
    def test_member_always_sees_them(self, api_client, auth_headers, test_user, flag):
        set_payment_flag(flag)
        event = _paid_event(test_user)
        assert self._venmo(api_client, event, **auth_headers) == "https://venmo.com/u/host"


@pytest.mark.django_db
class TestListEndpointFlagQueryCount:
    def test_payment_visibility_costs_no_flag_query(self, api_client, test_user):
        """can_see_payment_details reads no flag, so listing events must not
        query FeatureFlagState once per event — or at all."""
        for _ in range(6):
            _paid_event(test_user, event_type=EventType.OFFICIAL)
        with CaptureQueriesContext(connection) as ctx:
            assert api_client.get("/api/community/events/").status_code == 200
        assert not [q for q in ctx.captured_queries if "featureflagstate" in q["sql"].lower()]
