"""Shared utilities, schemas, and auth used across community API modules."""

import logging
import re

import phonenumbers
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from ninja.security import HttpBearer
from ninja_jwt.authentication import JWTAuth, JWTBaseAuthentication  # noqa: F401
from pydantic import BaseModel
from users.models import User as UserModel

from community._validation import Code, raise_validation

logger = logging.getLogger("pda.community")


class OptionalJWTAuth(JWTBaseAuthentication, HttpBearer):
    """JWT auth that returns AnonymousUser instead of None/401 when no/invalid token."""

    def authenticate(self, request: HttpRequest, token: str):
        try:
            return self.jwt_authenticate(request, token)
        except Exception:
            return AnonymousUser()

    def __call__(self, request: HttpRequest):
        result = super().__call__(request)
        # No Authorization header → super().__call__ returns None
        if result is None:
            return AnonymousUser()
        return result


_optional_jwt = OptionalJWTAuth()


class ErrorOut(BaseModel):
    detail: str


_DISPLAY_NAME_REJECT_RE = re.compile(r'[\d@#$%^&*()+=\[\]{}<>|\\/:;!?~`"]')


_DISPLAY_NAME_MAX_LENGTH = 64


def validate_display_name(name: str, field: str = "display_name") -> None:
    """Raise ValidationException if the display name is invalid.

    Allows Unicode letters, combining marks, apostrophes, hyphens, spaces, and periods.
    Rejects digits, email/URL characters, and names that contain no letters.
    """
    stripped = name.strip()
    if not stripped:
        raise_validation(Code.DisplayName.REQUIRED, field=field)
    if len(stripped) > _DISPLAY_NAME_MAX_LENGTH:
        raise_validation(
            Code.DisplayName.TOO_LONG, field=field, max_length=_DISPLAY_NAME_MAX_LENGTH
        )
    if _DISPLAY_NAME_REJECT_RE.search(stripped):
        raise_validation(Code.DisplayName.INVALID_CHARS, field=field)
    if all(c in " '-." for c in stripped):
        raise_validation(Code.DisplayName.NEEDS_A_LETTER, field=field)


def _validate_phone(raw: str, field: str = "phone_number") -> str:
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.phonenumberutil.NumberParseException:
        raise_validation(Code.Phone.INVALID, field=field)
    if not phonenumbers.is_valid_number(parsed):
        raise_validation(Code.Phone.INVALID, field=field)
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _authenticated_user(requesting_user) -> "UserModel | None":
    """Return the user if authenticated, None if anonymous."""
    if requesting_user is None or isinstance(requesting_user, AnonymousUser):
        return None
    return requesting_user


def _members_only(value, default, is_authed: bool):
    """Return value if user is authenticated, default otherwise."""
    return value if is_authed else default


def event_url(event) -> str:
    """Build the PDA event detail URL.

    Uses ``SITE_URL`` when configured (prod/staging); falls back to a relative
    path in dev so callers (or the frontend) can resolve it against the
    appropriate origin. Centralized here because outbound surfaces (calendar
    descriptions, future SMS / push / email reminders) all need the same link.
    """
    from django.conf import settings

    site_url = getattr(settings, "SITE_URL", "")
    return f"{site_url}/events/{event.id}" if site_url else f"/events/{event.id}"
