import asyncio
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from mcp.server.auth.provider import AuthorizationParams, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from mcp.shared.auth import OAuthToken as TokenResponse
from mcp_gateway.models import OAuthAuthCode, OAuthAuthRequest, OAuthGrant, OAuthToken
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


def _connect(provider: PdaOAuthProvider, user) -> TokenResponse:
    code = issue_auth_code(_pending_request(provider), user)
    loaded = asyncio.run(provider.load_authorization_code(_client_info(), code))
    assert loaded is not None
    return asyncio.run(provider.exchange_authorization_code(_client_info(), loaded))


def test_exchange_code_issues_tokens_once(test_user):
    provider = PdaOAuthProvider()
    code = issue_auth_code(_pending_request(provider), test_user)
    loaded = asyncio.run(provider.load_authorization_code(_client_info(), code))
    assert loaded is not None
    assert loaded.subject == str(test_user.pk)
    tokens = asyncio.run(provider.exchange_authorization_code(_client_info(), loaded))
    assert tokens.expires_in == 3600 and tokens.scope == "pda" and tokens.refresh_token
    assert asyncio.run(provider.load_authorization_code(_client_info(), code)) is None
    with pytest.raises(TokenError):
        asyncio.run(provider.exchange_authorization_code(_client_info(), loaded))


def test_expired_code_not_loaded(test_user):
    provider = PdaOAuthProvider()
    code = issue_auth_code(_pending_request(provider), test_user)
    OAuthAuthCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert asyncio.run(provider.load_authorization_code(_client_info(), code)) is None


def test_code_not_loaded_for_other_client_or_revoked_grant(test_user):
    provider = PdaOAuthProvider()
    code = issue_auth_code(_pending_request(provider), test_user)
    asyncio.run(provider.register_client(_client_info("client-2")))
    assert asyncio.run(provider.load_authorization_code(_client_info("client-2"), code)) is None
    OAuthGrant.objects.update(revoked_at=timezone.now())
    assert asyncio.run(provider.load_authorization_code(_client_info(), code)) is None


def test_load_access_token_returns_subject(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    access = asyncio.run(provider.load_access_token(tokens.access_token))
    assert access is not None
    assert access.subject == str(test_user.pk)
    assert access.client_id == "client-1"
    assert access.scopes == ["pda"]
    assert access.resource == RESOURCE
    assert access.expires_at and access.expires_at > timezone.now().timestamp()
    assert OAuthGrant.objects.get().last_used_at is not None
    assert tokens.refresh_token is not None
    assert asyncio.run(provider.load_access_token(tokens.refresh_token)) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [("is_paused", True), ("archived_at", "now"), ("needs_onboarding", True)],
)
def test_load_access_token_rejects_blocked_account(test_user, field, value):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    setattr(test_user, field, timezone.now() if value == "now" else value)
    test_user.save()
    assert asyncio.run(provider.load_access_token(tokens.access_token)) is None


def test_load_access_token_rejects_revoked_grant(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    OAuthGrant.objects.update(revoked_at=timezone.now())
    assert asyncio.run(provider.load_access_token(tokens.access_token)) is None


def test_load_access_token_rejects_expired_or_revoked_token(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    access = OAuthToken.objects.filter(kind=OAuthToken.Kind.ACCESS)
    access.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert asyncio.run(provider.load_access_token(tokens.access_token)) is None
    access.update(expires_at=timezone.now() + timedelta(hours=1), revoked_at=timezone.now())
    assert asyncio.run(provider.load_access_token(tokens.access_token)) is None


def test_load_access_token_touches_grant_at_most_once_a_minute(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    recent = timezone.now() - timedelta(seconds=30)
    OAuthGrant.objects.update(last_used_at=recent)
    asyncio.run(provider.load_access_token(tokens.access_token))
    assert OAuthGrant.objects.get().last_used_at == recent
    OAuthGrant.objects.update(last_used_at=recent - timedelta(minutes=1))
    asyncio.run(provider.load_access_token(tokens.access_token))
    assert OAuthGrant.objects.get().last_used_at > recent


def test_refresh_token_single_use(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    assert tokens.refresh_token is not None
    old = asyncio.run(provider.load_refresh_token(_client_info(), tokens.refresh_token))
    assert old is not None and old.subject == str(test_user.pk)
    rotated = asyncio.run(provider.exchange_refresh_token(_client_info(), old, ["pda"]))
    assert asyncio.run(provider.load_refresh_token(_client_info(), old.token)) is None
    with pytest.raises(TokenError):
        asyncio.run(provider.exchange_refresh_token(_client_info(), old, ["pda"]))
    assert rotated.refresh_token is not None
    assert asyncio.run(provider.load_refresh_token(_client_info(), rotated.refresh_token))
    assert asyncio.run(provider.load_access_token(rotated.access_token))
    assert OAuthGrant.objects.count() == 1


def test_refresh_token_not_loaded_for_other_client_or_revoked_grant(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    assert tokens.refresh_token is not None
    asyncio.run(provider.register_client(_client_info("client-2")))
    load = provider.load_refresh_token
    assert asyncio.run(load(_client_info("client-2"), tokens.refresh_token)) is None
    OAuthGrant.objects.update(revoked_at=timezone.now())
    assert asyncio.run(load(_client_info(), tokens.refresh_token)) is None


def test_revoke_token(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    assert tokens.refresh_token is not None
    access = asyncio.run(provider.load_access_token(tokens.access_token))
    refresh = asyncio.run(provider.load_refresh_token(_client_info(), tokens.refresh_token))
    assert access is not None and refresh is not None
    asyncio.run(provider.revoke_token(access))
    assert asyncio.run(provider.load_access_token(tokens.access_token)) is None
    asyncio.run(provider.revoke_token(refresh))
    assert asyncio.run(provider.load_refresh_token(_client_info(), refresh.token)) is None
