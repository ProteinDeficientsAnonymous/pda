"""Helpers for httpOnly refresh cookie (React SPA).

Design:
- Cookie name: `refresh_token`. HttpOnly, Secure (prod only), SameSite=Lax.
- Lifetime matches NINJA_JWT REFRESH_TOKEN_LIFETIME.
- Flutter (legacy) still reads `refresh` from the JSON body — we write both
  the cookie AND the body field until the Flutter client is retired.
- React reads only from the cookie.

Per .claude/rules/standards-django-flutter-integration.md: the API prefix
lives on the route, not the base URL, so cookie Path=/ is correct.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse

REFRESH_COOKIE_NAME = "refresh_token"


def _cookie_max_age_seconds() -> int:
    lifetime = settings.NINJA_JWT["REFRESH_TOKEN_LIFETIME"]
    return int(lifetime.total_seconds())


def set_refresh_cookie(response: HttpResponse, refresh_token: str) -> None:
    """Attach the refresh token as an httpOnly cookie.

    Safe on both dev (HTTP) and prod (HTTPS): `secure` follows settings.
    """
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=_cookie_max_age_seconds(),
        httponly=True,
        secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        path="/",
    )


def clear_refresh_cookie(response: HttpResponse) -> None:
    """Clear the refresh cookie on logout / refresh failure."""
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def read_refresh_cookie(request: HttpRequest) -> str | None:
    return request.COOKIES.get(REFRESH_COOKIE_NAME)
