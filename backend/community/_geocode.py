"""Geocoding proxy — avoids direct browser calls to Photon (blocks COEP)."""

import logging
from typing import Any

import httpx
from config.auth import gated_jwt
from django.http import HttpRequest
from ninja import Query, Router
from pydantic import BaseModel, Field

from community._shared import ErrorOut

logger = logging.getLogger("pda")

router = Router()

_PHOTON_URL = "https://photon.komoot.io/api/"


class GeocodeQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(5, ge=1, le=10)


class GeocodeOut(BaseModel):
    type: str | None = None
    features: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/geocode/", auth=gated_jwt, response={200: GeocodeOut, 502: ErrorOut})
def geocode(request: HttpRequest, params: Query[GeocodeQuery]):
    """Proxy geocoding requests to Photon, biased toward NYC."""
    try:
        resp = httpx.get(
            _PHOTON_URL,
            params={
                "q": params.q,
                "limit": params.limit,
                "lat": 40.7128,
                "lon": -74.006,
                "bbox": "-74.2591,40.4774,-73.7004,40.9176",  # NYC metro
                "countrycode": "us",
            },
            headers={"User-Agent": "Mozilla/5.0"},  # Photon blocks requests without a browser UA
            timeout=5.0,
        )
        resp.raise_for_status()
        return 200, resp.json()
    except (httpx.HTTPError, ValueError) as e:
        # Expected upstream failures: httpx.HTTPError covers timeout, connection
        # error, and non-2xx (TimeoutException is a subclass); ValueError covers
        # JSON-decode failures when a 2xx response carries a non-JSON body.
        # Log with request context but no PII — the query text is user input.
        logger.warning("geocode proxy error: limit=%s error=%s", params.limit, e)
        return 502, {"detail": "geocoding service unavailable — try again"}
