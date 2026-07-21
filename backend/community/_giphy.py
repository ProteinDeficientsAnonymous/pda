import logging

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

_GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"


class GiphyQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(24, ge=1, le=48)


class GiphyResult(BaseModel):
    id: str
    title: str
    preview_url: str
    original_url: str


class GiphySearchOut(BaseModel):
    results: list[GiphyResult]


def _parse_result(gif: dict) -> GiphyResult | None:
    images = gif.get("images", {})
    preview = images.get("fixed_width_small") or images.get("preview_gif") or {}
    original = images.get("original") or {}
    if not preview.get("url") or not original.get("url"):
        return None
    return GiphyResult(
        id=gif.get("id", ""),
        title=gif.get("title", ""),
        preview_url=preview["url"],
        original_url=original["url"],
    )


@router.get(
    "/giphy/search/",
    auth=gated_jwt,
    response={200: GiphySearchOut, 502: ErrorOut, 503: ErrorOut},
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/m")
def giphy_search(request: HttpRequest, params: Query[GiphyQuery]):
    """Proxy GIF search to Giphy — keeps GIPHY_API_KEY server-side."""
    api_key = getattr(settings, "GIPHY_API_KEY", "")
    if not api_key:
        return 503, {"detail": "gif search is not configured"}

    try:
        resp = httpx.get(
            _GIPHY_SEARCH_URL,
            params={
                "api_key": api_key,
                "q": params.q,
                "limit": params.limit,
                "rating": "pg-13",
                "lang": "en",
            },
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("giphy proxy error: q_len=%s error=%s", len(params.q), e)
        return 502, {"detail": "gif search unavailable — try again"}

    results = [r for r in (_parse_result(g) for g in data.get("data", [])) if r is not None]
    return 200, {"results": results}
