import pytest
from community.models import Event, EventStatus


@pytest.mark.django_db
class TestCreateDevTestEvents:
    def test_create_default_count_local(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        events = response.json()["events"]
        assert len(events) == 1
        assert events[0]["title"].startswith("[test] ")
        assert events[0]["status"] == EventStatus.DRAFT

    def test_create_allowed_on_staging(self, api_client, auth_headers, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"count": 3},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert len(response.json()["events"]) == 3
        assert Event.objects.filter(title__startswith="[test] ").count() == 3

    def test_bulk_titles_are_unique(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"count": 5},
            content_type="application/json",
            **auth_headers,
        )
        titles = [e["title"] for e in response.json()["events"]]
        assert len(set(titles)) == 5

    def test_404s_on_production(self, api_client, auth_headers, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404
        assert Event.objects.filter(title__startswith="[test] ").count() == 0

    def test_unauthenticated_401s(self, api_client, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_count_over_max_rejected(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"count": 21},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.django_db
class TestDeleteDevTestEvents:
    def test_deletes_only_prefixed_events(self, api_client, auth_headers, monkeypatch, test_user):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        Event.objects.create(title="[test] abcd1234", created_by=test_user)
        Event.objects.create(title="a real event", created_by=test_user)

        response = api_client.delete("/api/community/dev/test-events/", **auth_headers)

        assert response.status_code == 200
        assert Event.objects.filter(title__startswith="[test] ").count() == 0
        assert Event.objects.filter(title="a real event").exists()

    def test_404s_on_production(self, api_client, auth_headers, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
        response = api_client.delete("/api/community/dev/test-events/", **auth_headers)
        assert response.status_code == 404
