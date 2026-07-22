import logging
from typing import Literal

import httpx
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.conf import settings
from django.http import HttpRequest
from ninja import Query, Router
from pydantic import BaseModel, Field

from community._shared import ErrorOut

logger = logging.getLogger("pda")

router = Router()

_GIPHY_GIFS_URL = "https://api.giphy.com/v1/gifs/search"
_PEXELS_URL = "https://api.pexels.com/v1/search"
_DEFAULT_QUERY = "celebration"


class GiphyQuery(BaseModel):
    q: str = Field(_DEFAULT_QUERY, max_length=100)
    limit: int = Field(24, ge=1, le=48)


class GiphyResult(BaseModel):
    id: str
    title: str
    preview_url: str
    original_url: str
    source: Literal["gif", "photo"]


class GiphySearchOut(BaseModel):
    results: list[GiphyResult]


def _parse_gif(gif: dict) -> GiphyResult | None:
    images = gif.get("images", {})
    preview = images.get("fixed_width") or images.get("fixed_width_small") or {}
    # downsized_large caps at ~8 MB (still animated) so we stay under the 10 MB
    # event-photo limit; fall back to the uncapped original if it's missing.
    full = images.get("downsized_large") or images.get("original") or {}
    if not preview.get("url") or not full.get("url"):
        return None
    return GiphyResult(
        id=gif.get("id", ""),
        title=gif.get("title", ""),
        preview_url=preview["url"],
        original_url=full["url"],
        source="gif",
    )


def _parse_photo(photo: dict) -> GiphyResult | None:
    src = photo.get("src", {})
    preview = src.get("medium") or src.get("small") or ""
    # "large" caps the longest edge at ~940px — well under the 10 MB limit.
    full = src.get("large") or src.get("original") or ""
    if not preview or not full:
        return None
    return GiphyResult(
        id=f"pexels-{photo.get('id', '')}",
        title=photo.get("alt", ""),
        preview_url=preview,
        original_url=full,
        source="photo",
    )


def _fetch_gifs(api_key: str, query: str, limit: int) -> list[dict]:
    resp = httpx.get(
        _GIPHY_GIFS_URL,
        params={
            "api_key": api_key,
            "q": query,
            "limit": limit,
            "rating": "pg-13",
            "lang": "en",
        },
        timeout=5.0,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def _fetch_photos(api_key: str, query: str, limit: int) -> list[dict]:
    resp = httpx.get(
        _PEXELS_URL,
        params={"query": query, "per_page": limit},
        headers={"Authorization": api_key},
        timeout=5.0,
    )
    resp.raise_for_status()
    return resp.json().get("photos", [])


@router.get(
    "/giphy/search/",
    auth=gated_jwt,
    response={200: GiphySearchOut, 502: ErrorOut, 503: ErrorOut},
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def giphy_search(request: HttpRequest, params: Query[GiphyQuery]):
    """Proxy image search — animated gifs from Giphy + still photos from Pexels.

    Keeps both API keys server-side. Each source is optional: whichever key is
    configured contributes results, so the picker still works with only one.
    """
    giphy_key = getattr(settings, "GIPHY_API_KEY", "")
    pexels_key = getattr(settings, "PEXELS_API_KEY", "")
    if not giphy_key and not pexels_key:
        return 503, {"detail": "image search is not configured"}

    query = params.q.strip() or _DEFAULT_QUERY
    gif_limit = params.limit - params.limit // 3
    photo_limit = params.limit - gif_limit

    try:
        gifs = _fetch_gifs(giphy_key, query, gif_limit) if giphy_key else []
        photos = _fetch_photos(pexels_key, query, photo_limit) if pexels_key else []
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("image proxy error: q_len=%s error=%s", len(query), e)
        return 502, {"detail": "image search unavailable — try again"}

    results = [
        r
        for r in (
            *(_parse_gif(g) for g in gifs),
            *(_parse_photo(p) for p in photos),
        )
        if r is not None
    ]
    return 200, {"results": results}
