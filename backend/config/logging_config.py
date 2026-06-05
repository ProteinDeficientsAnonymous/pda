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
    "api-key",
    "apikey",
    "jwt",
    "session",
    "sessionid",
    "csrftoken",
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
    "phone",
)
# Shared "sensitive key" fragment used by BOTH the free-text regex and the
# extras key-name regex below, so the two can never drift. A keyword may carry
# `_`/`-`-separated prefix AND suffix segments — `access_token`, `refresh_token`,
# `client_secret`, `x-api-key`, `session_id`, `password_hash` — which is the most
# common shape for real credentials; those segments are part of the match so they
# are preserved in the output. (`phone` + the suffix segment already covers
# `phone_number`, so it is not listed separately.)
_KEY_CORE = r"(?:[A-Za-z0-9]+[-_])*(?:" + "|".join(_SENSITIVE_KEYWORDS) + r")(?:[-_][A-Za-z0-9]+)*"
# Free-text matcher. The `(?<![A-Za-z0-9])` left boundary and trailing `\b` only
# allow a separator or non-word char on either side, so letter-glued words
# (`telephone`, `geocode`, `megaphone`, `code` inside `geocode`) don't fire. Keys
# may appear quoted in serialized dicts/JSON (`'otp': '123'`, `"otp": "123"`), so
# allow an optional closing quote before the separator.
#
# The value is redacted in FULL — including embedded spaces — so it stops only at:
#   * the closing quote, for a quoted value;
#   * the next `key=`/`key:` pair (lookahead `\s+[\w-]+\s*[=:]`), so space-separated
#     pairs like `token=abc user=alice otp=999` redact each secret independently
#     and leave the non-secret pair intact;
#   * a pair delimiter (`;`, `,`, `&`) — cookie/query/header style; or
#   * end of line.
# This scrubs space-containing single values (`password: my secret pass phrase`,
# `authorization: Negotiate <cred>`) in full while never swallowing a sibling pair.
_SENSITIVE_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?P<key>" + _KEY_CORE + r")\b"
    r"(?P<sep>[\"']?\s*[=:]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|.+?(?=\s+[\w-]+\s*[=:]|[;,&\n]|$))",
    re.IGNORECASE,
)

# E.164 phone number pattern: + followed by 10-15 digits.
_E164_RE = re.compile(r"\+\d{10,15}")

# Matches a dict key (in structured extras) that is itself sensitive, so the whole
# value is redacted regardless of its content (e.g. {"authorization": "Bearer x"}).
# Same `_KEY_CORE` as the free-text matcher, `^...$`-anchored so letter-glued names
# (`telephone`, `geocode`) stay out.
_SENSITIVE_KEY_NAME_RE = re.compile(r"^" + _KEY_CORE + r"$", re.IGNORECASE)


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
    """Recursively redact sensitive data in extras.

    Plain numbers/bools/None pass through untouched. Strings, bytes, and arbitrary
    objects are redacted on their text form, because `JsonFormatter` serializes
    extras with ``json.dumps(default=str)`` — so any secret in a ``bytes`` payload or
    in a custom object's ``str()`` would otherwise reach the output *after* this
    filter ran. Redacting here closes that gap.
    """
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {k: _redact_dict_entry(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_redact_value(v) for v in value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return _redact_text(value.decode("utf-8", errors="replace"))
    # Arbitrary object: redact its string form, matching how the formatter will
    # ultimately serialize it (json.dumps(default=str)).
    return _redact_text(str(value))


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive data from log messages and structured extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Redaction must never raise: a filter that raises propagates straight out
        # of the `logger.*()` call (Python only wraps Handler.emit in handleError,
        # not the filter chain), which would crash the code that logged. Redaction
        # touches caller-supplied extras — including objects whose __str__ may raise
        # — so on any failure fall back to dropping the record's content rather than
        # emitting it unredacted or letting the exception escape.
        try:
            self._redact(record)
        except Exception:
            record.msg = "[REDACTION FAILED — content suppressed]"
            record.args = ()
            for key in tuple(record.__dict__):
                if key not in _STANDARD_FIELDS:
                    record.__dict__[key] = "[REDACTED]"
        return True

    @staticmethod
    def _redact(record: logging.LogRecord) -> None:
        # Redact the fully-rendered message, then collapse args so that the
        # message and its format args can never desync. record.getMessage()
        # applies %-formatting when args are present and is a no-op otherwise.
        record.msg = _redact_text(record.getMessage())
        record.args = ()

        # Scrub sensitive values in structured extras emitted by JsonFormatter.
        # Reuses _redact_dict_entry so top-level extras and nested-dict values
        # apply the same "sensitive key name → redact whole value, else recurse"
        # rule (e.g. extra={"password": x} and extra={"d": {"password": x}}).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS:
                record.__dict__[key] = _redact_dict_entry(key, value)
