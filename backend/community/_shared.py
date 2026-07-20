import logging
import re
from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from ninja.security import HttpBearer
from ninja_jwt.authentication import JWTAuth, JWTBaseAuthentication  # noqa: F401
from ninja_jwt.exceptions import AuthenticationFailed, TokenError
from pydantic import BaseModel
from users.models import User as UserModel

from community._validation import Code, raise_validation

logger = logging.getLogger("pda.community")


class OptionalJWTAuth(JWTBaseAuthentication, HttpBearer):
    """JWT auth that returns AnonymousUser instead of None/401 when no/invalid token."""

    def authenticate(self, request: HttpRequest, token: str):
        try:
            return self.jwt_authenticate(request, token)
        except (AuthenticationFailed, TokenError):
            # Genuinely-invalid / expired / unparseable token — treat the
            # caller as anonymous (public endpoints stay reachable).
            return AnonymousUser()
        except Exception:
            # Anything else (DB error, misconfiguration) is unexpected: log it
            # so it stays observable, but still degrade to anonymous rather
            # than 500 a public endpoint.
            logger.warning("optional jwt auth: unexpected error", exc_info=True)
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


def render_template_placeholders(body: str, placeholders: dict[str, str]) -> str:
    """Substitute ``${NAME}``-style placeholders in an admin-editable template body."""
    for name, value in placeholders.items():
        body = body.replace(f"${{{name}}}", value)
    return body


_WHATSAPP_KNOWN_HOSTS = {"chat.whatsapp.com", "wa.me", "whats.app"}


def _normalize_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _strip_www(host: str) -> str:
    return host.removeprefix("www.")


def require_url_path(url: str, field: str) -> str:
    """Validate that a URL has a non-trivial path (not bare domain)."""
    if not url:
        return url
    normalized = _normalize_url(url)
    try:
        parsed = urlparse(normalized)
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    if not parsed.netloc:
        raise_validation(Code.Url.INVALID, field=field)
    path = parsed.path.rstrip("/")
    if not path:
        raise_validation(Code.Url.PATH_REQUIRED, field=field)
    return normalized


def validate_whatsapp_url(url: str, field: str) -> str:
    if not url:
        return url
    try:
        parsed = urlparse(_normalize_url(url))
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    host = _strip_www(parsed.netloc.lower())
    if host not in _WHATSAPP_KNOWN_HOSTS:
        raise_validation(
            Code.Url.WHATSAPP_NOT_RECOGNIZED,
            field=field,
            allowed_hosts=sorted(_WHATSAPP_KNOWN_HOSTS),
        )
    return require_url_path(url, field=field)


def flatten_to_single_line(value: str) -> str:
    r"""Collapse every line-break in untrusted text into a single space.

    splitlines() covers \n \r \r\n \v \f \x1c-\x1e \x85    , so this
    neutralizes any sink where a newline in user input would let the value
    inject extra structure — an email header line, a GitHub issue title, etc.
    """
    return " ".join(value.splitlines()).strip()


def _authenticated_user(requesting_user) -> "UserModel | None":
    """Return the user if authenticated, None if anonymous."""
    if requesting_user is None or isinstance(requesting_user, AnonymousUser):
        return None
    return requesting_user


def _members_only(value, default, is_authed: bool):
    """Return value if user is authenticated, default otherwise."""
    return value if is_authed else default
