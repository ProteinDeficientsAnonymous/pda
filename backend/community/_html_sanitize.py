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
vocabulary changes.

This mirrors the frontend's DOMPurify pass (`frontend/src/utils/sanitize.ts`):
the backend is the canonical sanitizer for non-browser consumers (emails, API
clients), the frontend is defense-in-depth for content that never round-trips.
"""

from __future__ import annotations

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
# _filter_style_properties below) — the renderers' sole inline-style use. `class`
# is handled separately via _allowed_classes, not listed here.
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "target", "role"},
    "img": {"src", "alt"},
    "p": {"style"},
    "h1": {"style"},
    "h2": {"style"},
    "h3": {"style"},
}

# Link/image schemes. Relative URLs (e.g. uploaded "/media/..." images) carry no
# scheme and are always allowed by nh3. `data:` is intentionally excluded — the
# renderers only emit remote/uploaded URLs, so it would add surface with no gain.
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

# CTA anchors are the only class-bearing element the renderers produce.
_ALLOWED_CLASSES = {"a": {"cta", "cta--primary", "cta--secondary"}}

# The only CSS property the renderers emit; nh3 drops every other declaration and
# normalises the value, so style="position:absolute;..." collapses to nothing.
_FILTER_STYLE_PROPERTIES = {"text-align"}

# `rel="noopener noreferrer"` is force-injected on every anchor, blocking
# reverse-tabnabbing on target="_blank" links regardless of what was emitted.
_LINK_REL = "noopener noreferrer"


def sanitize_content_html(html: str) -> str:
    """Sanitize rendered rich-text HTML against the renderers' allowlist.

    Strips disallowed tags/attributes, rejects non-http(s)/mailto URL schemes on
    href/src, constrains inline style to `text-align`, and forces a safe `rel` on
    links. Returns "" for empty input.
    """
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        allowed_classes=_ALLOWED_CLASSES,
        filter_style_properties=_FILTER_STYLE_PROPERTIES,
        link_rel=_LINK_REL,
        strip_comments=True,
    )
