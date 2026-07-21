"""Tests for the Giphy search proxy endpoint (key gating + response shape)."""

from unittest.mock import patch

import httpx
import pytest

_URL = "/api/community/giphy/search/"


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.django_db
class TestGiphyBounds:
    def test_rejects_empty_query(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q=", **auth_headers)
        assert response.status_code == 422

    def test_rejects_oversized_query(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q={'a' * 101}", **auth_headers)
        assert response.status_code == 422

    def test_rejects_limit_over_max(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q=carrot&limit=49", **auth_headers)
        assert response.status_code == 422

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(f"{_URL}?q=carrot")
        assert response.status_code == 401


@pytest.mark.django_db
class TestGiphySearch:
    def test_returns_503_when_key_missing(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = ""
        response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 503

    def test_parses_and_filters_results(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "test-key"
        payload = {
            "data": [
                {
                    "id": "abc",
                    "title": "carrot dance",
                    "images": {
                        "fixed_width_small": {"url": "https://example.com/abc-small.gif"},
                        "original": {"url": "https://example.com/abc.gif"},
                    },
                },
                # Missing images entirely — must be dropped, not crash the request.
                {"id": "no-images", "title": "broken"},
            ]
        }
        with patch("community._giphy.httpx.get") as mock_get:
            mock_get.return_value = _FakeResp(payload)
            response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "results": [
                {
                    "id": "abc",
                    "title": "carrot dance",
                    "preview_url": "https://example.com/abc-small.gif",
                    "original_url": "https://example.com/abc.gif",
                }
            ]
        }

    def test_upstream_error_returns_502(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "test-key"
        with patch(
            "community._giphy.httpx.get",
            side_effect=httpx.ConnectError("refused"),
        ):
            response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"]
