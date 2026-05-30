import json
import logging
import re
from datetime import UTC, datetime

# Fields from LogRecord that are part of the standard schema (not extras).
_STANDARD_FIELDS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class JsonFormatter(logging.Formatter):
    """Outputs log records as single-line JSON for Railway log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any extra fields added via `logger.info("msg", extra={...})`.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and key not in entry:
                entry[key] = value

        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


# Patterns that indicate sensitive data (case-insensitive key=value style).
# The value capture is non-greedy and stops at whitespace, comma, or quote so
# that multiple k=v pairs on one line each get redacted independently rather
# than the first match swallowing the rest of the line. Quoted values are
# captured in full (including spaces) up to the closing quote.
#
# `code` is intentionally NOT a bare keyword: it over-matches benign diagnostic
# lines (`HTTP code: 500`, `status_code: 200`, `error code: 42`, `geocode: ...`).
# Sensitive verification/auth codes are covered by `otp` and the explicit
# `*_code` variants below.
_SENSITIVE_KEYWORDS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "jwt",
    "session",
    "cookie",
    "set-cookie",
    "refresh",
    "otp",
    "verification_code",
    "verification-code",
    "auth_code",
    "auth-code",
    "reset_code",
    "reset-code",
    "phone_number",
    "phone",
)
# Optional auth scheme whose credential follows the scheme word (e.g. "Bearer <token>").
_AUTH_SCHEME = r"(?:Bearer|Basic|Token|JWT)\s+"
# Keys may appear bare (`otp=123`) or quoted in serialized dicts/JSON
# (`'otp': '123'`, `"otp": "123"`), so allow an optional closing quote between
# the key and the separator. Keywords are anchored with \b so partial-word
# matches (e.g. `code` inside `geocode`, `phone` inside `telephone`) don't fire.
_SENSITIVE_KEY_RE = re.compile(
    r"\b(?P<key>" + "|".join(_SENSITIVE_KEYWORDS) + r")\b"
    r"(?P<sep>[\"']?\s*[=:]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|(?:" + _AUTH_SCHEME + r")?\S+)",
    re.IGNORECASE,
)

# E.164 phone number pattern: + followed by 10-15 digits.
_E164_RE = re.compile(r"\+\d{10,15}")

# Matches a dict key (in structured extras) that is itself sensitive, so the
# whole value is redacted regardless of its content (e.g. {"authorization": "Bearer x"}).
_SENSITIVE_KEY_NAME_RE = re.compile(
    r"^(?:" + "|".join(_SENSITIVE_KEYWORDS) + r")$",
    re.IGNORECASE,
)


def _redact_text(text: str) -> str:
    """Redact sensitive key=value pairs and phone numbers in a string."""
    redacted = _SENSITIVE_KEY_RE.sub(
        lambda m: f"{m.group('key')}{m.group('sep')}[REDACTED]",
        text,
    )
    return _E164_RE.sub("[REDACTED]", redacted)


def _redact_dict_entry(key: object, value: object) -> object:
    """Redact a dict value whose key name is sensitive; otherwise recurse."""
    if isinstance(key, str) and _SENSITIVE_KEY_NAME_RE.match(key):
        return "[REDACTED]"
    return _redact_value(value)


def _redact_value(value: object) -> object:
    """Recursively redact sensitive data in extras, preserving non-string types."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {k: _redact_dict_entry(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_redact_value(v) for v in value)
    return value


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive data from log messages and structured extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact the fully-rendered message, then collapse args so that the
        # message and its format args can never desync. record.getMessage()
        # applies %-formatting when args are present and is a no-op otherwise.
        record.msg = _redact_text(record.getMessage())
        record.args = ()

        # Scrub sensitive values in structured extras emitted by JsonFormatter.
        # If the extra's key name is itself sensitive (e.g. extra={"password": x}),
        # redact the whole value; otherwise recurse into the value's contents.
        for key, value in record.__dict__.items():
            if key in _STANDARD_FIELDS:
                continue
            if _SENSITIVE_KEY_NAME_RE.match(key):
                record.__dict__[key] = "[REDACTED]"
            else:
                record.__dict__[key] = _redact_value(value)

        return True
