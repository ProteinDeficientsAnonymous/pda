import asyncio
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from mcp_gateway.models import OAuthAuthCode, OAuthAuthRequest, OAuthGrant
from mcp_gateway.provider import AuthRequestNotPending, PdaOAuthProvider, issue_auth_code
from mcp_gateway.tokens import hash_secret

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

REDIRECT = "https://claude.ai/api/mcp/auth_callback"
RESOURCE = "https://pda.test/mcp"


def _client_info(client_id: str = "client-1") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_name="claude",
        redirect_uris=[REDIRECT],
        token_endpoint_auth_method="none",
        scope="pda",
    )


def _params(scopes: list[str] | None = None) -> AuthorizationParams:
    return AuthorizationParams(
        state="xyz",
        scopes=scopes,
        code_challenge="challenge",
        redirect_uri=REDIRECT,
        redirect_uri_provided_explicitly=True,
        resource=RESOURCE,
    )


def _pending_request(provider: PdaOAuthProvider) -> OAuthAuthRequest:
    info = _client_info()
    asyncio.run(provider.register_client(info))
    url = asyncio.run(provider.authorize(info, _params()))
    return OAuthAuthRequest.objects.get(pk=url.rsplit("=", 1)[1])


def test_register_and_get_client_roundtrip():
    provider = PdaOAuthProvider()
    info = _client_info()
    asyncio.run(provider.register_client(info))
    assert asyncio.run(provider.get_client("client-1")) == info
    assert asyncio.run(provider.get_client("missing")) is None


def test_authorize_creates_pending_request_and_returns_frontend_url():
    provider = PdaOAuthProvider()
    info = _client_info()
    asyncio.run(provider.register_client(info))
    url = asyncio.run(provider.authorize(info, _params()))
    assert url.startswith(settings.FRONTEND_BASE_URL + "/connect/authorize?request=")
    req = OAuthAuthRequest.objects.get(pk=url.rsplit("=", 1)[1])
    assert req.status == OAuthAuthRequest.Status.PENDING
    assert req.client.client_id == "client-1"
    assert req.expires_at > timezone.now()


def test_issue_auth_code_approves_request_and_stores_hashed_code(test_user):
    req = _pending_request(PdaOAuthProvider())
    code = issue_auth_code(req, test_user)
    row = OAuthAuthCode.objects.select_related("grant").get(code_hash=hash_secret(code))
    assert row.grant.user == test_user
    assert row.scopes == ["pda"]
    assert row.resource == RESOURCE
    assert row.redirect_uri == REDIRECT
    req.refresh_from_db()
    assert req.status == OAuthAuthRequest.Status.APPROVED
    assert req.user == test_user


def test_issue_auth_code_only_once(test_user):
    req = _pending_request(PdaOAuthProvider())
    issue_auth_code(req, test_user)
    with pytest.raises(AuthRequestNotPending):
        issue_auth_code(req, test_user)
    assert OAuthGrant.objects.count() == 1


def test_issue_auth_code_rejects_expired_request(test_user):
    req = _pending_request(PdaOAuthProvider())
    OAuthAuthRequest.objects.filter(pk=req.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(AuthRequestNotPending):
        issue_auth_code(req, test_user)
    assert not OAuthGrant.objects.exists()
