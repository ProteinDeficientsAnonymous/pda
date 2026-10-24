import asyncio

import httpx
import pytest
from config.asgi import application
from django.conf import settings
from mcp_gateway.asgi_router import McpDispatcher

from tests._mcp_helpers import REDIRECT

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

BASE = settings.MCP_PUBLIC_BASE_URL


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        return await client.request(method, path, **kwargs)


def _register(**metadata) -> httpx.Response:
    body = {"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none", **metadata}
    return asyncio.run(_request("POST", "/register", json=body))


def test_dispatcher_routes_lifespan_and_mcp_paths_to_mcp_app():
    seen = []

    def fake(label):
        async def app(scope, receive, send):
            seen.append((label, scope["type"], scope.get("path")))

        return app

    dispatcher = McpDispatcher(fake("django"), fake("mcp"))
    scopes = [
        {"type": "lifespan"},
        {"type": "http", "path": "/token"},
        {"type": "http", "path": "/.well-known/oauth-protected-resource/mcp"},
        {"type": "http", "path": "/mcp/"},
        {"type": "http", "path": "/api/auth/me/"},
        {"type": "websocket", "path": "/mcp"},
    ]
    for scope in scopes:
        asyncio.run(dispatcher(scope, None, None))
    assert [label for label, *_ in seen] == ["mcp", "mcp", "mcp", "django", "django", "django"]


def test_protected_resource_metadata():
    response = asyncio.run(_request("GET", "/.well-known/oauth-protected-resource/mcp"))
    assert response.status_code == 200
    assert response.json()["authorization_servers"] == [BASE]
    assert response.json()["resource"] == f"{BASE}/mcp"


def test_mcp_without_token_401_with_resource_metadata():
    response = asyncio.run(_request("POST", "/mcp", json={}))
    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["www-authenticate"]


def test_register_rejects_unknown_scope():
    response = _register(scope="admin")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client_metadata"


def test_register_defaults_to_pda_scope():
    response = _register()
    assert response.status_code == 201
    assert response.json()["scope"] == "pda"


def test_authorize_redirects_to_consent_screen():
    client_id = _register().json()["client_id"]
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "code_challenge": "x" * 43,
        "code_challenge_method": "S256",
        "resource": f"{BASE}/mcp",
    }
    response = asyncio.run(_request("GET", "/authorize", params=params))
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(f"{settings.FRONTEND_BASE_URL}/connect/authorize?request=")


def test_non_mcp_paths_still_reach_django():
    response = asyncio.run(_request("GET", "/api/auth/me/", headers={"host": "testserver"}))
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
