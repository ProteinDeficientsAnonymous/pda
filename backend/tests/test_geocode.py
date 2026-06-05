"""Tests for the geocode proxy endpoint (input bounds + upstream error handling)."""

import json
from unittest.mock import patch

import httpx
import pytest

_URL = "/api/community/geocode/"


class _FakeResp:
    def __init__(self, payload, *, json_error=None):
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self):
        return None

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


@pytest.mark.django_db
class TestGeocodeBounds:
    def test_rejects_limit_over_max(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q=cafe&limit=11", **auth_headers)
        assert response.status_code == 422

    def test_rejects_limit_below_min(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q=cafe&limit=0", **auth_headers)
        assert response.status_code == 422

    def test_rejects_oversized_query(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q={'a' * 201}&limit=5", **auth_headers)
        assert response.status_code == 422

    def test_rejects_empty_query(self, api_client, auth_headers):
        response = api_client.get(f"{_URL}?q=&limit=5", **auth_headers)
        assert response.status_code == 422

    def test_accepts_valid_request(self, api_client, auth_headers):
        with patch("community._geocode.httpx.get") as mock_get:
            mock_get.return_value = _FakeResp({"type": "FeatureCollection", "features": []})
            response = api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)
        assert response.status_code == 200
        assert response.json() == {"type": "FeatureCollection", "features": []}

    def test_passes_through_extra_top_level_fields(self, api_client, auth_headers):
        """The proxy must stay lossless — Photon's top-level bbox must reach the client."""
        payload = {
            "type": "FeatureCollection",
            "features": [],
            "bbox": [-74.2, 40.4, -73.7, 40.9],
        }
        with patch("community._geocode.httpx.get") as mock_get:
            mock_get.return_value = _FakeResp(payload)
            response = api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)
        assert response.status_code == 200
        assert response.json() == payload


@pytest.mark.django_db
class TestGeocodeUpstreamErrors:
    def test_timeout_returns_502(self, api_client, auth_headers):
        with patch(
            "community._geocode.httpx.get",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            response = api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)
        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"]

    def test_http_error_returns_502(self, api_client, auth_headers):
        with patch(
            "community._geocode.httpx.get",
            side_effect=httpx.ConnectError("refused"),
        ):
            response = api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)
        assert response.status_code == 502

    def test_non_json_2xx_body_returns_502(self, api_client, auth_headers):
        # Photon (or a proxy/CDN) returns HTTP 200 with a non-JSON body, so
        # raise_for_status() passes but resp.json() raises JSONDecodeError (a
        # ValueError). This must degrade to a graceful 502, not a 500.
        decode_error = json.JSONDecodeError("Expecting value", "<html>", 0)
        with patch("community._geocode.httpx.get") as mock_get:
            mock_get.return_value = _FakeResp(None, json_error=decode_error)
            response = api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)
        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"]

    def test_unexpected_error_is_not_swallowed(self, api_client, auth_headers):
        # A non-httpx error (programming bug) must surface, not masquerade as 502.
        with patch("community._geocode.httpx.get", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                api_client.get(f"{_URL}?q=brooklyn&limit=5", **auth_headers)

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(f"{_URL}?q=brooklyn&limit=5")
        assert response.status_code == 401
