from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from audit.models import AuditLogEntry
from django.utils import timezone
from mcp_gateway.models import OAuthAuthCode, OAuthAuthRequest, OAuthGrant

from tests._asserts import assert_error_code
from tests._mcp_helpers import REDIRECT, make_client, make_request

pytestmark = pytest.mark.django_db


def _url(request_id, action: str = "") -> str:
    return f"/api/connect/requests/{request_id}/{action}"


def _expire(req: OAuthAuthRequest) -> None:
    OAuthAuthRequest.objects.filter(pk=req.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


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


def test_approve_returns_redirect_with_code_and_state(api_client, auth_headers, test_user):
    req = make_request(state="xyz")
    resp = api_client.post(_url(req.id, "approve/"), **auth_headers)
    assert resp.status_code == 200
    url = resp.json()["redirect_url"]
    assert url.startswith(REDIRECT + "?")
    query = _query(url)
    assert query["state"] == ["xyz"]
    assert len(query["code"]) == 1
    assert OAuthAuthCode.objects.filter(grant__user=test_user).count() == 1


def test_approve_without_state_omits_state(api_client, auth_headers):
    req = make_request(state=None)
    resp = api_client.post(_url(req.id, "approve/"), **auth_headers)
    assert "state" not in _query(resp.json()["redirect_url"])


def test_approve_expired_request_410(api_client, auth_headers):
    req = make_request()
    _expire(req)
    resp = api_client.post(_url(req.id, "approve/"), **auth_headers)
    assert resp.status_code == 410
    assert_error_code(resp, "connect.request_expired")
    assert not OAuthGrant.objects.exists()


def test_approve_twice_409(api_client, auth_headers):
    req = make_request()
    assert api_client.post(_url(req.id, "approve/"), **auth_headers).status_code == 200
    resp = api_client.post(_url(req.id, "approve/"), **auth_headers)
    assert resp.status_code == 409
    assert_error_code(resp, "connect.request_already_used")
    assert OAuthGrant.objects.count() == 1


def test_approve_unknown_request_404(api_client, auth_headers):
    resp = api_client.post(_url("00000000-0000-0000-0000-000000000000", "approve/"), **auth_headers)
    assert resp.status_code == 404


def test_unauthenticated_approve_401(api_client):
    req = make_request()
    assert api_client.post(_url(req.id, "approve/")).status_code == 401
    assert not OAuthGrant.objects.exists()


def test_approve_is_audited(api_client, auth_headers, django_capture_on_commit_callbacks):
    req = make_request()
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(_url(req.id, "approve/"), **auth_headers)
    entry = AuditLogEntry.objects.get(action="mcp_connection_approved")
    assert entry.target_type == "mcp_connection"
    assert entry.target_id == str(OAuthGrant.objects.get().id)


def test_deny_returns_access_denied(api_client, auth_headers):
    req = make_request(state="xyz")
    resp = api_client.post(_url(req.id, "deny/"), **auth_headers)
    assert resp.status_code == 200
    url = resp.json()["redirect_url"]
    assert url.startswith(REDIRECT + "?")
    assert _query(url) == {"error": ["access_denied"], "state": ["xyz"]}
    req.refresh_from_db()
    assert req.status == OAuthAuthRequest.Status.DENIED
    assert not OAuthGrant.objects.exists()


def test_approve_after_deny_409(api_client, auth_headers):
    req = make_request()
    api_client.post(_url(req.id, "deny/"), **auth_headers)
    resp = api_client.post(_url(req.id, "approve/"), **auth_headers)
    assert resp.status_code == 409
    assert not OAuthGrant.objects.exists()


def test_deny_after_approve_409(api_client, auth_headers):
    req = make_request()
    api_client.post(_url(req.id, "approve/"), **auth_headers)
    resp = api_client.post(_url(req.id, "deny/"), **auth_headers)
    assert resp.status_code == 409
    req.refresh_from_db()
    assert req.status == OAuthAuthRequest.Status.APPROVED


def test_deny_expired_request_410(api_client, auth_headers):
    req = make_request()
    _expire(req)
    resp = api_client.post(_url(req.id, "deny/"), **auth_headers)
    assert resp.status_code == 410
    req.refresh_from_db()
    assert req.status == OAuthAuthRequest.Status.PENDING


def test_unauthenticated_deny_401(api_client):
    req = make_request()
    assert api_client.post(_url(req.id, "deny/")).status_code == 401
    req.refresh_from_db()
    assert req.status == OAuthAuthRequest.Status.PENDING


def test_deny_is_audited(api_client, auth_headers, django_capture_on_commit_callbacks):
    req = make_request()
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(_url(req.id, "deny/"), **auth_headers)
    entry = AuditLogEntry.objects.get(action="mcp_connection_denied")
    assert entry.target_type == "mcp_connection"
    assert entry.target_id == str(req.id)
