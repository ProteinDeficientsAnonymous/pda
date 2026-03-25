import pytest


@pytest.mark.django_db
class TestAuth:
    def test_login_valid(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "member@pda.org", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_invalid(self, api_client):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "nobody@pda.org", "password": "wrong"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_me_authenticated(self, api_client, test_user, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "member@pda.org"

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestJoinRequest:
    def test_submit_join_request(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "name": "Leafy Green",
                "email": "leafy@vegan.org",
                "pronouns": "they/them",
                "how_they_heard": "Word of mouth",
                "why_join": "I want to connect with other vegans in collective liberation work.",
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Leafy Green"

    def test_submit_join_request_missing_fields(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {"name": "Leafy", "email": "leafy@vegan.org"},
            content_type="application/json",
        )
        # Django Ninja returns 422 for Pydantic validation errors (missing required fields)
        assert response.status_code == 422


@pytest.mark.django_db
class TestEvents:
    def test_events_requires_auth(self, api_client):
        response = api_client.get("/api/community/events/")
        assert response.status_code == 401

    def test_events_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
