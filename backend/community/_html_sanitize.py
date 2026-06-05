"""Server-side HTML sanitization for rendered rich-text content.

The Delta / ProseMirror renderers build `content_html` by escaping text and
emitting a fixed vocabulary of tags. `html.escape` neutralises text, but it does
NOT strip dangerous URL schemes (`javascript:`, `data:`) from href/src, nor would
it catch a stray attribute if a renderer ever regressed. This module runs the
finished HTML through `nh3` (Python bindings to the Rust `ammonia` sanitizer) as
a single, audited security boundary.

`nh3` is configured to exactly match what the renderers emit — no more, no less:
allowing anything broader would widen the XSS surface; allowing less would
silently corrupt valid rendered content (alignment, CTA styling). Keep this
allowlist in sync with `_delta_html.py` / `_prosemirror_html.py` if their output
vocabulary changes — `test_html_sanitize.py` round-trips real renderer output
through here to catch drift.

This mirrors the frontend's DOMPurify pass (`frontend/src/utils/sanitize.ts`):
the backend is the canonical sanitizer for non-browser consumers (emails, API
clients), the frontend is defense-in-depth for content that never round-trips.
The two passes are kept value-for-value equivalent on URL handling and the
`text-align` allowlist (see `_attribute_filter` / `_normalize_url` and their
frontend mirror) so neither boundary is weaker — both normalise the same URL
obfuscations and accept the same case-insensitive alignment tokens.
"""

from __future__ import annotations

import re

import nh3

# Tags the renderers emit. Must stay in sync with _delta_html / _prosemirror_html.
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

# `style` is allowed only on block tags and only carries `text-align` (see
# _attribute_filter below, which validates the value) — the renderers' sole
# inline-style use. `class` is handled separately via _allowed_classes.
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "target", "role"},
    "img": {"src"},
    "p": {"style"},
    "h1": {"style"},
    "h2": {"style"},
    "h3": {"style"},
}

# Schemes allowed on link hrefs. Relative URLs (e.g. uploaded "/media/..."
# images) carry no scheme and are always allowed by nh3. `data:` is intentionally
# excluded — the renderers only emit remote/uploaded URLs, so it would add surface
# with no gain. `mailto:` is link-only; see `_attribute_filter` for why image
# `src` rejects it (matching the old hand-rolled image-scheme guard).
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

# CTA anchors are the only class-bearing element the renderers produce.
_ALLOWED_CLASSES = {"a": {"cta", "cta--primary", "cta--secondary"}}

# The renderers only ever emit `text-align: left|center|right` (the ProseMirror
# renderer gates on exactly these; the Delta renderer emits no alignment at all).
# Mirrors the frontend's ALLOWED_TEXT_ALIGN so the two boundaries agree. The
# regex is case-insensitive to match the frontend's `/i` flag, and `[a-z]+`
# (not `[a-z-]+`) so a hyphen-suffixed token like `center-ish` is captured whole
# and rejected the same way on both sides.
_ALLOWED_TEXT_ALIGN = {"left", "center", "right"}
_TEXT_ALIGN_RE = re.compile(r"text-align:\s*([a-z]+)", re.IGNORECASE)

# Characters a browser's URL parser ignores at the start of an href/src (ASCII
# whitespace + C0 controls). Stripping them before the protocol-relative check
# closes the " //evil.com" / "\t//evil.com" bypass.
_URL_LEADING_IGNORED = "".join(chr(c) for c in range(0x21)) + "\x7f"

# `rel="noopener noreferrer"` is force-injected on every anchor, blocking
# reverse-tabnabbing on target="_blank" links regardless of what was emitted.
_LINK_REL = "noopener noreferrer"


def _normalize_url(value: str) -> str:
    """Collapse an href/src to the form a browser actually resolves.

    Browsers ignore leading ASCII whitespace / C0 controls and treat backslashes
    as forward slashes in special-scheme URLs, so `/\\evil.com` and ` //evil.com`
    both resolve to `//evil.com`. Canonicalising here means the stored value
    matches what every consumer (browser, email, API client) sees, removing the
    parser differential that lets obfuscated protocol-relative URLs slip past a
    naive `startswith("//")` check.
    """
    return value.lstrip(_URL_LEADING_IGNORED).replace("\\", "/")


def _attribute_filter(tag: str, attribute: str, value: str) -> str | None:
    """Per-attribute scrub run by `nh3.clean` after its scheme allowlist.

    `url_schemes` already drops `javascript:`/`data:`/etc. before this runs, but
    it does NOT inspect scheme-less URLs or constrain CSS *values*. This closes
    both gaps at the same audited boundary:

    - Protocol-relative URLs (`//evil.com`) carry no scheme, so nh3 treats them
      as relative and would keep them — an off-site / remote-load vector. Reject
      them on `href`/`src` (after normalising browser-equivalent obfuscations),
      while leaving genuine relative paths (`/media/...`). The normalised value
      is re-emitted so `https:/\\evil.com` is stored as the `https://evil.com`
      it resolves to, not the ambiguous original.
    - `mailto:` is valid for links but inert-and-pointless on an image `src`;
      reject it there to preserve the old image-scheme guard (http/https only).
    - `style` may only carry a single `text-align` declaration with an allowlisted
      value. nh3's `filter_style_properties` keeps the property but NOT the value,
      so `text-align: behavior(...)` would survive; rebuild the value here instead.

    Returning `None` drops the attribute; returning a string replaces its value.
    """
    if attribute in ("href", "src"):
        normalized = _normalize_url(value)
        if normalized.startswith("//"):
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
