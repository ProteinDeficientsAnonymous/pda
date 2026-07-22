"""Tests for the image search proxy endpoint (key gating + response shape)."""

from unittest.mock import patch

import httpx
import pytest

_URL = "/api/community/giphy/search/"

_GIF_PAYLOAD = {
    "data": [
        {
            "id": "abc",
            "title": "carrot dance",
            "images": {
                "fixed_width": {"url": "https://example.com/abc-small.gif"},
                "original": {"url": "https://example.com/abc.gif"},
            },
        },
        # Missing images entirely — must be dropped, not crash the request.
        {"id": "no-images", "title": "broken"},
    ]
}

_PHOTO_PAYLOAD = {
    "photos": [
        {
            "id": 123,
            "alt": "fresh carrots",
            "src": {
                "medium": "https://example.com/123-medium.jpg",
                "large": "https://example.com/123-large.jpg",
            },
        }
    ]
}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _by_url(gif_payload=None, photo_payload=None):
    """Route the Giphy vs Pexels call by URL so tests don't depend on call order."""

    def _side_effect(url, *args, **kwargs):
        if "pexels" in url:
            return _FakeResp(photo_payload or {"photos": []})
        return _FakeResp(gif_payload or {"data": []})

    return _side_effect


@pytest.mark.django_db
class TestGiphyBounds:
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
class TestImageSearch:
    def test_returns_503_when_both_keys_missing(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = ""
        settings.PEXELS_API_KEY = ""
        response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 503

    def test_parses_and_merges_gifs_and_photos(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = "pexels-key"
        with patch(
            "community._giphy.httpx.get",
            side_effect=_by_url(_GIF_PAYLOAD, _PHOTO_PAYLOAD),
        ):
            response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "results": [
                {
                    "id": "abc",
                    "title": "carrot dance",
                    "preview_url": "https://example.com/abc-small.gif",
                    "original_url": "https://example.com/abc.gif",
                    "source": "gif",
                },
                {
                    "id": "pexels-123",
                    "title": "fresh carrots",
                    "preview_url": "https://example.com/123-medium.jpg",
                    "original_url": "https://example.com/123-large.jpg",
                    "source": "photo",
                },
            ]
        }

    def test_gif_prefers_downsized_large_over_original(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = ""
        payload = {
            "data": [
                {
                    "id": "big",
                    "title": "party",
                    "images": {
                        "fixed_width": {"url": "https://example.com/big-small.gif"},
                        "downsized_large": {"url": "https://example.com/big-large.gif"},
                        "original": {"url": "https://example.com/big.gif"},
                    },
                }
            ]
        }
        with patch("community._giphy.httpx.get", side_effect=_by_url(gif_payload=payload)):
            response = api_client.get(f"{_URL}?q=party", **auth_headers)
        assert response.status_code == 200
        assert response.json()["results"][0]["original_url"] == "https://example.com/big-large.gif"

    def test_works_with_only_pexels_key(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = ""
        settings.PEXELS_API_KEY = "pexels-key"
        with patch(
            "community._giphy.httpx.get",
            side_effect=_by_url(photo_payload=_PHOTO_PAYLOAD),
        ) as mock_get:
            response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 200
        assert [r["source"] for r in response.json()["results"]] == ["photo"]
        # Only the Pexels endpoint should be hit when Giphy is unconfigured.
        assert all("pexels" in call.args[0] for call in mock_get.call_args_list)

    def test_upstream_error_returns_502(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = "pexels-key"
        with patch(
            "community._giphy.httpx.get",
            side_effect=httpx.ConnectError("refused"),
        ):
            response = api_client.get(f"{_URL}?q=carrot", **auth_headers)
        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"]

    def test_missing_query_uses_default_term(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = "pexels-key"
        with patch("community._giphy.httpx.get", side_effect=_by_url()) as mock_get:
            response = api_client.get(_URL, **auth_headers)
        assert response.status_code == 200
        assert _query_terms(mock_get) == {"celebration"}

    def test_blank_query_uses_default_term(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = "pexels-key"
        with patch("community._giphy.httpx.get", side_effect=_by_url()) as mock_get:
            response = api_client.get(f"{_URL}?q=", **auth_headers)
        assert response.status_code == 200
        assert _query_terms(mock_get) == {"celebration"}

    def test_splits_limit_between_gifs_and_photos(self, api_client, auth_headers, settings):
        settings.GIPHY_API_KEY = "giphy-key"
        settings.PEXELS_API_KEY = "pexels-key"
        with patch("community._giphy.httpx.get", side_effect=_by_url()) as mock_get:
            response = api_client.get(f"{_URL}?q=carrot&limit=9", **auth_headers)
        assert response.status_code == 200
        limits = {}
        for call in mock_get.call_args_list:
            params = call.kwargs["params"]
            if "pexels" in call.args[0]:
                limits["photo"] = params["per_page"]
            else:
                limits["gif"] = params["limit"]
        assert limits == {"gif": 6, "photo": 3}


def _query_terms(mock_get) -> set[str]:
    """Collect the search term from each upstream call (Giphy `q`, Pexels `query`)."""
    terms = set()
    for call in mock_get.call_args_list:
        params = call.kwargs["params"]
        terms.add(params.get("q") or params.get("query"))
    return terms
