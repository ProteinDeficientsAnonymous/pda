import pytest


@pytest.mark.django_db
class TestCalendarToken:
    def test_get_token_empty_before_generation(self, api_client, auth_headers):
        resp = api_client.get("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == ""
        assert data["feed_url"] == ""

    def test_generate_token(self, api_client, auth_headers):
        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) > 0
        assert "calendar/feed/?token=" in data["feed_url"]

    def test_regenerate_token_replaces_old(self, api_client, auth_headers):
        resp1 = api_client.post("/api/community/calendar/token/", **auth_headers)
        token1 = resp1.json()["token"]
        resp2 = api_client.post("/api/community/calendar/token/", **auth_headers)
        token2 = resp2.json()["token"]
        assert token1 != token2

    def test_get_token_returns_existing(self, api_client, auth_headers):
        api_client.post("/api/community/calendar/token/", **auth_headers)
        resp = api_client.get("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["token"]) > 0

    def test_token_endpoints_require_auth(self, api_client):
        assert api_client.get("/api/community/calendar/token/").status_code == 401
        assert api_client.post("/api/community/calendar/token/").status_code == 401


@pytest.mark.django_db
class TestCalendarFeed:
    def test_feed_returns_ics(self, api_client, auth_headers, test_user):
        from community.models import Event

        # Generate token
        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        # Create an event
        from django.utils import timezone

        Event.objects.create(
            title="Test Potluck",
            description="Bring snacks!",
            location="The park",
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        # Fetch feed
        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        content = resp.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "Test Potluck" in content
        assert "The park" in content

    def test_feed_defaults_end_to_start_plus_2h(self, api_client, auth_headers, test_user):
        import datetime as dt

        from community.models import Event

        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        start = dt.datetime(2026, 7, 1, 18, 0, tzinfo=dt.UTC)
        Event.objects.create(
            title="No End Time",
            start_datetime=start,
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "DTEND" in content
        # start + 2h = 20:00 UTC
        assert "20260701T200000" in content

    def test_feed_includes_links_in_description(self, api_client, auth_headers, test_user):
        from community.models import Event
        from django.utils import timezone

        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        Event.objects.create(
            title="Linked Event",
            description="Join us!",
            start_datetime=timezone.now(),
            whatsapp_link="https://chat.whatsapp.com/abc",
            partiful_link="https://partiful.com/e/xyz",
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        # Unfold ICS line continuations before checking
        content = resp.content.decode().replace("\r\n ", "")
        assert "Join us!" in content
        assert "WhatsApp: https://chat.whatsapp.com/abc" in content
        assert "Partiful: https://partiful.com/e/xyz" in content

    def test_feed_invalid_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/?token=bogus-token")
        assert resp.status_code == 403

    def test_feed_missing_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestSingleEventIcs:
    def test_returns_ics_for_existing_event(self, api_client, test_user):
        from community.models import Event
        from django.utils import timezone

        event = Event.objects.create(
            title="Picnic in the Park",
            description="Bring hummus!",
            location="Prospect Park",
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        content = resp.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "Picnic in the Park" in content
        assert "Prospect Park" in content

    def test_returns_404_for_nonexistent_event(self, api_client):
        import uuid

        resp = api_client.get(f"/api/community/events/{uuid.uuid4()}/ics/")
        assert resp.status_code == 404
