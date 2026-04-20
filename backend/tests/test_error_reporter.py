"""Tests for POST /api/community/error-report/.

Broader coverage already exists in `test_community.py::TestErrorReport` and
`test_logging.py::TestErrorReportEndpoint`; this module pins the minimum
contract (happy path + unauth rejection) alongside the frontend reporter
util so the feature's end-to-end surface lives in one place.
"""

import pytest


@pytest.mark.django_db
class TestErrorReporterEndpoint:
    def test_happy_path_returns_201(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {
                "error": "boom",
                "stack_trace": "at src/screens/Foo.tsx:42",
                "route": "/calendar",
                "client_timestamp": "2026-04-19T12:00:00Z",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["detail"] == "Error report received."

    def test_rejects_unauthenticated_request(self, api_client):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "boom"},
            content_type="application/json",
        )
        assert response.status_code == 401
