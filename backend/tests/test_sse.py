"""Tests for the SSE notification stream endpoint."""

import pytest
from ninja_jwt.tokens import RefreshToken


def _access_token(user) -> str:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)  # ty: ignore[unresolved-attribute]


@pytest.mark.django_db
class TestSseAuth:
    def test_missing_token_returns_401(self, api_client):
        response = api_client.get("/api/notifications/stream/")
        assert response.status_code == 401
        assert response.json()["detail"] == "token required"

    def test_invalid_token_returns_401(self, api_client):
        response = api_client.get("/api/notifications/stream/?token=garbage")
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid token"

    def test_valid_token_does_not_get_401(self, test_user, api_client):
        """A valid JWT should pass auth — endpoint may return 200 (streaming) or
        fail for infra reasons (PG connect), but must not return 401."""
        token = _access_token(test_user)
        response = api_client.get(f"/api/notifications/stream/?token={token}")
        assert response.status_code != 401
