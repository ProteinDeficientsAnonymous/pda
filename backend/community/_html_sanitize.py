"""Server-side HTML sanitization for rendered rich-text content.

Runs renderer output (`content_html`) through `nh3` as a single audited security
boundary, configured to exactly match the Delta / ProseMirror vocabulary. Mirrors
the frontend DOMPurify pass in `frontend/src/utils/sanitize.ts`; the two are kept
equivalent on URL handling and the `text-align` allowlist. Keep the allowlists in
sync with `_delta_html.py` / `_prosemirror_html.py`; `test_html_sanitize.py`
round-trips real renderer output to catch drift.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

import nh3

_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "s",
    "strong",
    "u",
    "ul",
}

_ALLOWED_ATTRIBUTES = {
    "a": {"href", "target", "role"},
    "img": {"src"},
    "p": {"style"},
    "h1": {"style"},
    "h2": {"style"},
    "h3": {"style"},
}

# `data:` is excluded deliberately; the renderers only emit remote/uploaded URLs.
# `mailto:` is link-only — `_attribute_filter` rejects it on image `src`.
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

_ALLOWED_CLASSES = {"a": {"cta", "cta--primary", "cta--secondary"}}

_ALLOWED_TEXT_ALIGN = {"left", "center", "right"}
# Anchored to a declaration boundary (start or after `;`) so a prefixed property
# like `-webkit-text-align` doesn't match, while a real `text-align` among
# `;`-separated siblings still does.
_TEXT_ALIGN_RE = re.compile(r"(?:^|;)\s*text-align:\s*([a-z]+)", re.IGNORECASE)

_URL_REMOVED_CONTROLS = re.compile(r"[\t\n\r]")
_URL_LEADING_SLASHES = re.compile(r"^/{2,}")

_LINK_REL = "noopener noreferrer"


def _normalize_url(value: str) -> str:
    """Collapse an href/src to the form a browser actually resolves.

    Replicates the browser transforms that `urlsplit` skips: strip tab/LF/CR from
    anywhere, fold backslashes to `/` only in the authority/path (not the query,
    so `?x=a\\b` survives), and collapse 2+ leading slashes to `//`.
    """
    value = _URL_REMOVED_CONTROLS.sub("", value)
    cut = next((i for i, ch in enumerate(value) if ch in "?#"), len(value))
    value = value[:cut].replace("\\", "/") + value[cut:]
    return _URL_LEADING_SLASHES.sub("//", value)


def _is_protocol_relative(value: str) -> bool:
    """True if `value` resolves to an off-site authority with no explicit scheme.

    Parses rather than substring-matches so obfuscation variants (`//evil.com`,
    `/\\evil`, ...) are caught. An unparseable URL fails closed (treated as
    protocol-relative) rather than slipping through nh3's swallowed exception.
    """
    try:
        parts = urlsplit(value)
    except ValueError:
        return True
    return bool(parts.netloc) and not parts.scheme


def _attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    """Per-attribute scrub run by `nh3.clean`; returns None to drop the attribute.

    Closes gaps nh3's scheme allowlist leaves open: protocol-relative URLs (no
    scheme, so nh3 keeps them), `mailto:` on image `src`, and `style` values (nh3
    keeps the `text-align` property but not its value).

    SAFETY: the scheme check runs on the original value before this filter, and
    nh3 does not re-validate what we return. `_normalize_url` must never
    manufacture a scheme from safe input — its transforms cannot introduce a `:`,
    so they are safe; preserve that invariant.
    """
    if attribute in ("href", "src"):
        normalized = _normalize_url(value)
        if _is_protocol_relative(normalized):
            return None
        value = normalized
    if attribute == "src" and value.lower().startswith("mailto:"):
        return None
    if attribute == "style":
        match = _TEXT_ALIGN_RE.search(value)
        alignment = match.group(1).lower() if match else None
        if alignment in _ALLOWED_TEXT_ALIGN:
            return f"text-align: {alignment}"
        return None
    return value


def sanitize_content_html(html: str) -> str:
    """Sanitize rendered rich-text HTML against the renderers' allowlist.

    Strips disallowed tags/attributes, rejects dangerous and protocol-relative
    URLs on href/src, constrains inline style to an allowlisted `text-align`
    value, and forces a safe `rel` on links. Returns "" for empty input.
    """
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        allowed_classes=_ALLOWED_CLASSES,
        attribute_filter=_attribute_filter,
        link_rel=_LINK_REL,
        strip_comments=True,
    )
