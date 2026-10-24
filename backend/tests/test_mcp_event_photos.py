import asyncio
import io
from unittest.mock import patch

import httpx
import pytest
from audit.models import AuditLogEntry
from community.models import Event
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import pda_mcp
from mcp_gateway.tools import event_photos
from PIL import Image
from users.models import User

from tests.conftest import future_iso
from tests.test_giphy import _GIF_PAYLOAD, _PHOTO_PAYLOAD, _by_url
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
PEXELS = "https://images.pexels.com/photos/1/pexels-photo-1.jpeg"


def _image(content: bytes | None = None) -> httpx.Response:
    if content is None:
        buf = io.BytesIO()
        Image.new("RGB", (20, 20)).save(buf, format="JPEG")
        content = buf.getvalue()
    return httpx.Response(200, content=content, headers={"content-type": "image/jpeg"})


def _call(user, name, **args):
    token = _signed_in(user)
    try:
        return asyncio.run(pda_mcp.call_tool(name, args)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


@pytest.fixture
def event(test_user):
    return Event.objects.create(title="x", start_datetime=future_iso(days=3), created_by=test_user)


@pytest.fixture
def remote(monkeypatch):
    requested, responses = [], {}

    def handler(request):
        requested.append(str(request.url))
        return responses.get(str(request.url), httpx.Response(404))

    real = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    return requested, responses


def test_search_returns_candidates(test_user, settings):
    settings.GIPHY_API_KEY = settings.PEXELS_API_KEY = "k"
    with patch("community._giphy.httpx.get", side_effect=_by_url(_GIF_PAYLOAD, _PHOTO_PAYLOAD)):
        result = _call(test_user, "search_event_photos", query="carrots")["result"]
    assert [r["source"] for r in result] == ["gif", "photo"]
    assert result[1]["image_url"] == "https://example.com/123-large.jpg"


def test_set_photo_on_own_event_stores_and_audits(test_user, event, remote):
    remote[1][PEXELS] = _image()
    result = _call(test_user, "set_event_photo", event_id=str(event.id), image_url=PEXELS)
    event.refresh_from_db()
    assert event.photo and result["photo_url"]
    assert result["url"].endswith(f"/events/{event.slug or event.id}")
    entry = AuditLogEntry.objects.get(action="event_photo_uploaded", target_id=str(event.id))
    assert (entry.actor, entry.details["via"]) == (test_user, "mcp")


def test_non_host_refused_by_view(event, remote):
    other = User.objects.create_user(phone_number="+12025550199", password="x", first_name="o")
    remote[1][PEXELS] = _image()
    with pytest.raises(ToolError, match="403"):
        _call(other, "set_event_photo", event_id=str(event.id), image_url=PEXELS)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/x.jpg",
        "http://images.pexels.com/x.jpg",
        "https://images.pexels.com@evil.example/x.jpg",
        "https://images.pexels.com:8443/x.jpg",
    ],
)
def test_disallowed_urls_never_fetched(test_user, event, remote, url):
    with pytest.raises(ToolError, match="search_event_photos"):
        _call(test_user, "set_event_photo", event_id=str(event.id), image_url=url)
    assert remote[0] == []


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(302, headers={"location": "https://evil.example/x.jpg"}), "couldn't fetch"),
        (_image(b"x" * 101), "too large"),
    ],
)
def test_redirect_and_oversize_rejected(event, remote, monkeypatch, response, error):
    monkeypatch.setattr(event_photos, "_MAX_EVENT_PHOTO_SIZE", 100)
    remote[1][PEXELS] = response
    with pytest.raises(ToolError, match=error):
        _call(event.created_by, "set_event_photo", event_id=str(event.id), image_url=PEXELS)
    event.refresh_from_db()
    assert (remote[0], event.photo.name) == ([PEXELS], "")
