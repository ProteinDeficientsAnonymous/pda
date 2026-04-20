"""Geocoding proxy — avoids direct browser calls to Photon (blocks COEP)."""

import logging

import httpx
from django.http import HttpRequest
from ninja import Router
from ninja_jwt.authentication import JWTAuth

from community._shared import ErrorOut

logger = logging.getLogger("pda")

router = Router()

_PHOTON_URL = "https://photon.komoot.io/api/"


@router.get("/geocode/", auth=JWTAuth(), response={200: dict, 502: ErrorOut})
def geocode(request: HttpRequest, q: str, limit: int = 5):
    """Proxy geocoding requests to Photon, biased toward NYC."""
    try:
        resp = httpx.get(
            _PHOTON_URL,
            params={
                "q": q,
                "limit": limit,
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
    except Exception as e:
        logger.warning("Geocoding proxy error: %s", e)
        return 502, {"detail": "geocoding service unavailable — try again"}
