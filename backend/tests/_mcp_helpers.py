from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from mcp_gateway.models import OAuthAuthRequest, OAuthClient, OAuthGrant, OAuthToken
from mcp_gateway.tokens import ACCESS_TTL, REFRESH_TTL, hash_secret, new_secret

REDIRECT = "https://claude.ai/api/mcp/auth_callback"


def make_client(client_id: str | None = None, name: str = "claude") -> OAuthClient:
    client_id = client_id or f"client-{uuid4().hex[:8]}"
    info = OAuthClientInformationFull(
        client_id=client_id,
        client_name=name,
        redirect_uris=[REDIRECT],
        token_endpoint_auth_method="none",
        scope="pda",
    )
    return OAuthClient.objects.create(
        client_id=client_id, client_name=name, info=info.model_dump(mode="json")
    )


def make_request(client: OAuthClient | None = None, state: str | None = "xyz") -> OAuthAuthRequest:
    params = AuthorizationParams(
        state=state,
        scopes=None,
        code_challenge="challenge",
        redirect_uri=REDIRECT,
        redirect_uri_provided_explicitly=True,
        resource="https://pda.test/mcp",
    )
    return OAuthAuthRequest.objects.create(
        client=client or make_client(),
        params=params.model_dump(mode="json"),
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def make_grant(user, client: OAuthClient | None = None) -> OAuthGrant:
    return OAuthGrant.objects.create(user=user, client=client or make_client())


def make_tokens(grant: OAuthGrant) -> str:
    access, now = new_secret(), timezone.now()
    for secret, kind, ttl in (
        (access, OAuthToken.Kind.ACCESS, ACCESS_TTL),
        (new_secret(), OAuthToken.Kind.REFRESH, REFRESH_TTL),
    ):
        OAuthToken.objects.create(
            token_hash=hash_secret(secret), kind=kind, grant=grant, expires_at=now + ttl
        )
    return access
