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
# (not `[a-z-]+`) so a hyphen-suffixed token like `center-ish` captures just
# `center` — accepted and rebuilt to `text-align: center` identically on both
# sides (output is always a fixed allowlisted token, so no value can inject).
_ALLOWED_TEXT_ALIGN = {"left", "center", "right"}
_TEXT_ALIGN_RE = re.compile(r"text-align:\s*([a-z]+)", re.IGNORECASE)

# Characters a browser's URL parser ignores at the START of an href/src (ASCII
# C0 controls 0x00–0x1F + space 0x20, plus DEL 0x7F). Stripped before the
# protocol-relative check to close the " //evil.com" / "\t//evil.com" bypass.
_URL_LEADING_IGNORED = "".join(chr(c) for c in range(0x21)) + "\x7f"

# Tab / LF / CR are removed from ANYWHERE in a URL by browsers before parsing
# (the WHATWG URL "remove all ASCII tab or newline" step), so an embedded one
# can't be used to split up a protocol-relative form like `/\t/evil.com`.
_URL_REMOVED_CONTROLS = re.compile(r"[\t\n\r]")

# `rel="noopener noreferrer"` is force-injected on every anchor, blocking
# reverse-tabnabbing on target="_blank" links regardless of what was emitted.
_LINK_REL = "noopener noreferrer"


def _normalize_url(value: str) -> str:
    """Collapse an href/src to the form a browser actually resolves.

    Mirrors the browser URL parser so the stored value matches what every
    consumer (browser, email, API client) sees, removing the parser differential
    that lets obfuscated protocol-relative URLs slip past a naive `startswith`:

    - Tab/LF/CR are removed from anywhere in the string (browsers do this before
      parsing), so `/\\t/evil.com` can't hide a protocol-relative form.
    - Leading ASCII whitespace / C0 controls are ignored.
    - Backslashes fold to forward slashes, but ONLY in the authority/path
      (everything before the first `?` or `#`) — browsers don't fold in the
      query/fragment, so folding the whole string would corrupt a legitimate
      backslash in a query string (`?x=a\\b`).

    So `/\\evil.com`, ` //evil.com`, and `https:/\\evil.com` all canonicalise to
    a leading `//` (rejected by the caller), while legit URLs are untouched.
    """
    value = _URL_REMOVED_CONTROLS.sub("", value).lstrip(_URL_LEADING_IGNORED)
    cut = next((i for i, ch in enumerate(value) if ch in "?#"), len(value))
    return value[:cut].replace("\\", "/") + value[cut:]


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

    SAFETY: nh3 does NOT re-validate the value this returns against `url_schemes`
    — the scheme check runs on the ORIGINAL value before this filter, so a
    `javascript:`/`data:` URL is already gone by the time we run. That means
    `_normalize_url` must never *manufacture* a dangerous scheme from a safe
    input; its transforms (strip whitespace/controls, fold leading backslashes)
    cannot introduce a `:`, so they are safe. Keep that invariant if you extend
    it — anything that could synthesise a scheme would become a stored-XSS hole.
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
