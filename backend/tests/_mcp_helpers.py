import base64
import hashlib
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.utils import timezone
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull
from mcp_gateway.asgi_router import McpDispatcher
from mcp_gateway.models import OAuthAuthRequest, OAuthClient, OAuthGrant, OAuthToken
from mcp_gateway.provider import issue_auth_code
from mcp_gateway.server import build_mcp_app, pda_mcp
from mcp_gateway.tokens import ACCESS_TTL, REFRESH_TTL, hash_secret, new_secret

REDIRECT = "https://claude.ai/api/mcp/auth_callback"
BASE = settings.FRONTEND_BASE_URL.rstrip("/")
RESOURCE = f"{BASE}/mcp"


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


@asynccontextmanager
async def mcp_client():
    # A session manager runs once, so each test needs a fresh MCP app.
    app = McpDispatcher(get_asgi_application(), build_mcp_app())
    async with pda_mcp.session_manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
            yield client


async def connect(client: httpx.AsyncClient, user) -> str:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    registration = {"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none"}
    client_id = (await client.post("/register", json=registration)).json()["client_id"]
    authorize = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
        },
    )
    request_id = parse_qs(urlsplit(authorize.headers["location"]).query)["request"][0]
    auth_request = await OAuthAuthRequest.objects.select_related("client").aget(pk=request_id)
    code = await sync_to_async(issue_auth_code)(auth_request, user)
    token = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
    )
    return token.json()["access_token"]


async def rpc(client: httpx.AsyncClient, token: str, method: str, **params) -> httpx.Response:
    return await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
    )
