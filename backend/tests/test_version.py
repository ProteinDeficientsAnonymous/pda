import pytest


@pytest.mark.django_db
class TestGetVersion:
    def test_get_version_unauthenticated(self, api_client):
        response = api_client.get("/api/community/version/")
        assert response.status_code == 200
        data = response.json()
        assert "commit_sha" in data
        assert "commit_sha_short" in data
        assert "environment" in data

    def test_get_version_local_fallback(self, api_client, monkeypatch):
        monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.get("/api/community/version/")
        assert response.status_code == 200
        data = response.json()
        assert data["commit_sha"] == "dev"
        assert data["commit_sha_short"] == "dev"
        assert data["environment"] == "local"

    def test_get_version_from_railway_env(self, api_client, monkeypatch):
        monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abc1234def5678")
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")
        response = api_client.get("/api/community/version/")
        assert response.status_code == 200
        data = response.json()
        assert data["commit_sha"] == "abc1234def5678"
        assert data["commit_sha_short"] == "abc1234"
        assert data["environment"] == "staging"
