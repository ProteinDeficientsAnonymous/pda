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

    def test_feed_invalid_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/?token=bogus-token")
        assert resp.status_code == 403

    def test_feed_missing_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/")
        assert resp.status_code == 403
