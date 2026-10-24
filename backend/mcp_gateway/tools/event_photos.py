from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from community._event_actions import upload_event_photo
from community._event_schemas import _MAX_EVENT_PHOTO_SIZE
from community._giphy import GiphyQuery, giphy_search
from django.core.files.uploadedfile import SimpleUploadedFile
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from mcp_gateway.server import BASE_URL, current_user, pda_tool
from mcp_gateway.view_calls import call_view

_GIPHY_HOSTS = {"i.giphy.com", "media.giphy.com", *(f"media{n}.giphy.com" for n in range(5))}
PHOTO_HOSTS = frozenset({"images.pexels.com", *_GIPHY_HOSTS})
_FETCH_FAILED = "couldn't fetch that photo, pick another"


@pda_tool(
    description=(
        "search pexels photos and giphy gifs for an event photo. show the planner a few "
        "candidates (preview_url) and let them pick one; never search the open web for images."
    )
)
async def search_event_photos(
    query: Annotated[str, Field(description="what the photo should show", max_length=100)],
) -> list[dict[str, Any]]:
    params = GiphyQuery(q=query, limit=6)
    body = await call_view(giphy_search, await current_user(), params=params)
    if "results" not in body:
        raise ToolError(body.get("detail", "image search unavailable"))
    keys = ("id", "title", "preview_url", "source")
    return [{**{k: r[k] for k in keys}, "image_url": r["original_url"]} for r in body["results"]]


def _checked_url(url: str) -> str:
    parts = urlsplit(url)
    # netloc must be a bare allowlisted host: no userinfo, no port.
    if parts.scheme != "https" or parts.netloc.lower() not in PHOTO_HOSTS:
        raise ToolError("only image_url values from search_event_photos can be used")
    return url


async def _download(url: str) -> SimpleUploadedFile:
    body = bytearray()
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            async with client.stream("GET", _checked_url(url)) as resp:
                if resp.status_code != 200:
                    raise ToolError(_FETCH_FAILED)
                content_type = resp.headers.get("content-type", "").split(";")[0].strip()
                async for chunk in resp.aiter_bytes():
                    body += chunk
                    if len(body) > _MAX_EVENT_PHOTO_SIZE:
                        raise ToolError("that photo is too large, pick another")
    except httpx.HTTPError as exc:
        raise ToolError(_FETCH_FAILED) from exc
    ext = content_type.rsplit("/", 1)[-1] or "jpg"
    return SimpleUploadedFile(f"photo.{ext}", bytes(body), content_type=content_type)


@pda_tool(
    description=(
        "set an event's photo to a search_event_photos candidate (pass its image_url). if the "
        "event is published, confirm the chosen photo with the user first: members will see it. "
        "this can't use the planner's own photo or any other url; for that, tell them to add it "
        f"on the event page at {BASE_URL}/events/<event id>."
    )
)
async def set_event_photo(
    event_id: Annotated[UUID, Field(description="the event to update")],
    image_url: Annotated[str, Field(description="image_url of a search_event_photos result")],
) -> dict[str, Any]:
    photo = await _download(image_url)
    user = await current_user()
    event = await call_view(upload_event_photo, user, event_id=event_id, photo=photo)
    return {
        "id": event["id"],
        "title": event["title"],
        "photo_url": event["photo_url"],
        "url": f"{BASE_URL}/events/{event['slug'] or event['id']}",
    }
