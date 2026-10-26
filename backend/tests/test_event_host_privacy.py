import pytest
from community.models import Event
from django.utils import timezone

OMITTED_FROM_LIST = {
    *("whatsapp_link", "partiful_link", "other_link", "venmo_link", "cashapp_link"),
    *("zelle_info", "latitude", "longitude", "created_by_id", "created_by_name"),
    *("co_host_names", "co_host_photo_urls"),
}


@pytest.fixture
def hosted_event(test_user):
    event = Event.objects.create(
        title="Hosted", start_datetime=timezone.now(), created_by=test_user
    )
    event.co_hosts.add(test_user)
    return event


@pytest.mark.django_db
class TestEventHostPrivacy:
    def test_list_omits_links_payment_and_host_identity(
        self, api_client, auth_headers, test_user, hosted_event
    ):
        anon, authed = (
            next(e for e in api_client.get("/api/community/events/", **h).json())
            for h in ({}, auth_headers)
        )
        assert not OMITTED_FROM_LIST & (anon.keys() | authed.keys())
        assert anon["co_host_ids"] == []
        assert authed["co_host_ids"] == [str(test_user.id)]

    def test_detail_hides_hosts_from_anonymous(
        self, api_client, auth_headers, test_user, hosted_event
    ):
        anon, authed = (
            api_client.get(f"/api/community/events/{hosted_event.id}/", **h).json()
            for h in ({}, auth_headers)
        )
        assert (anon["created_by_id"], anon["created_by_name"]) == (None, None)
        assert anon["co_host_ids"] == anon["co_host_names"] == []
        assert authed["co_host_ids"] == [str(test_user.id)]
        assert authed["co_host_names"]
