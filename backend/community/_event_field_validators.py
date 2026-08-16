import re
from urllib.parse import urlparse

import phonenumbers

from community._shared import require_url_path
from community._validation import Code, raise_validation

# Loose email check for free-text Zelle — EmailStr/DNS is overkill here.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _looks_like_email(s: str) -> bool:
    return bool(_EMAIL_RE.match(s))


def _looks_like_phone(s: str) -> bool:
    """Accept E.164 (+15551234567) or any string phonenumbers can parse as US."""
    try:
        parsed = phonenumbers.parse(s, "US")
    except phonenumbers.phonenumberutil.NumberParseException:
        return False
    return phonenumbers.is_valid_number(parsed)


def _validate_zelle_info(v: str | None) -> str | None:
    """Zelle is a free-text field but should be either an email or a phone number."""
    if v is None or v == "":
        return v
    stripped = v.strip()
    if _looks_like_email(stripped) or _looks_like_phone(stripped):
        return stripped
    raise_validation(Code.Zelle.INVALID, field="zelle_info")


def _validate_max_attendees(v: int | None) -> int | None:
    """Accept null (unlimited) or an integer >= 1. Reject 0 and negatives."""
    if v is None:
        return v
    if v < 1:
        raise_validation(
            Code.Event.MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE,
            field="max_attendees",
        )
    return v


def _normalize_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _strip_www(host: str) -> str:
    return host.removeprefix("www.")


def _validate_partiful_url(url: str, field: str) -> str:
    if not url:
        return url
    try:
        parsed = urlparse(_normalize_url(url))
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    host = _strip_www(parsed.netloc.lower())
    if "partiful.com" not in host:
        raise_validation(Code.Url.PARTIFUL_NOT_RECOGNIZED, field=field)
    return require_url_path(url, field=field)


def _validate_generic_url(url: str, field: str) -> str:
    # Accepts either a bare domain (fast.com) or a full URL and normalizes to
    # a full https:// URL on the way in. We don't require a path — "other_link"
    # is commonly used for landing pages and flyers.
    if not url:
        return url
    normalized = _normalize_url(url)
    try:
        parsed = urlparse(normalized)
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    if not parsed.netloc or "." not in parsed.netloc:
        raise_validation(Code.Url.INVALID, field=field)
    if parsed.scheme not in ("http", "https"):
        raise_validation(Code.Url.SCHEME_MUST_BE_HTTP_OR_HTTPS, field=field)
    return normalized
