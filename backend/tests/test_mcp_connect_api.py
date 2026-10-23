from datetime import timedelta

import pytest
from django.utils import timezone
from mcp_gateway.models import OAuthAuthRequest

from tests._asserts import assert_error_code
from tests._mcp_helpers import make_client, make_request

pytestmark = pytest.mark.django_db


def _url(request_id, action: str = "") -> str:
    return f"/api/connect/requests/{request_id}/{action}"


def _expire(req: OAuthAuthRequest) -> None:
    OAuthAuthRequest.objects.filter(pk=req.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )


def test_get_request_shows_client_and_redirect_host(api_client, auth_headers):
    req = make_request(make_client(name="claude"))
    resp = api_client.get(_url(req.id), **auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["client_name"] == "claude"
    assert body["redirect_host"] == "claude.ai"


def test_get_unknown_request_404(api_client, auth_headers):
    resp = api_client.get(_url("00000000-0000-0000-0000-000000000000"), **auth_headers)
    assert resp.status_code == 404
    assert_error_code(resp, "connect.request_not_found")


def test_get_expired_request_410(api_client, auth_headers):
    req = make_request()
    _expire(req)
    resp = api_client.get(_url(req.id), **auth_headers)
    assert resp.status_code == 410
    assert_error_code(resp, "connect.request_expired")


def test_get_used_request_409(api_client, auth_headers):
    req = make_request()
    OAuthAuthRequest.objects.filter(pk=req.pk).update(status=OAuthAuthRequest.Status.APPROVED)
    resp = api_client.get(_url(req.id), **auth_headers)
    assert resp.status_code == 409
    assert_error_code(resp, "connect.request_already_used")


def test_unauthenticated_get_401(api_client):
    assert api_client.get(_url(make_request().id)).status_code == 401
