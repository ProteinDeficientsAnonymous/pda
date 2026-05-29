"""URL-scheme allowlisting for the HTML renderers (defense-in-depth).

Both `_delta_html` and `_prosemirror_html` HTML-escape the values they emit,
but `html.escape` does NOT strip dangerous URL schemes — `javascript:alert(1)`
survives escaping intact and stays clickable. These helpers reject anything
that isn't an http/https/mailto link (plus relative URLs) before the value is
escaped and written into an href/src attribute.

Lives in its own module so both renderers can import it without creating an
import cycle with `_content_render`, which imports the renderers.
"""

from __future__ import annotations

# Schemes permitted for link hrefs. Relative URLs (no scheme, or starting with
# "/", "#", "?") are also allowed and handled separately in safe_link_href.
_SAFE_LINK_SCHEMES = ("http://", "https://", "mailto:")

# Schemes permitted for image src. Data URLs are intentionally excluded — the
# renderers only ever emit remote image URLs, so allowing data: would only add
# an XSS surface (data:text/html, embedded SVG payloads) with no benefit.
_SAFE_IMAGE_SCHEMES = ("http://", "https://")


def _has_scheme(value: str) -> bool:
    """True if `value` carries an explicit URL scheme.

    A scheme is letters/digits/+/-/. followed by a colon before any "/", "?"
    or "#". This catches "javascript:", "data:", "vbscript:" etc. while treating
    "/path", "#frag", "?q=1" and "page" as relative (no scheme).
    """
    for ch in value:
        if ch in ("/", "?", "#"):
            return False
        if ch == ":":
            return True
        if not (ch.isalnum() or ch in "+-."):
            return False
    return False


def safe_link_href(raw: str | None) -> str:
    """Return `raw` if it is a safe link target, else "".

    Allows http/https/mailto and relative URLs; rejects javascript:, data:,
    vbscript:, and any other scheme. Returns the *unescaped* value — callers are
    responsible for HTML-escaping the result.
    """
    value = (raw or "").strip()
    if not value:
        return ""
    if not _has_scheme(value):
        # Relative URL ("/path", "#frag", "page") — safe.
        return value
    if value.lower().startswith(_SAFE_LINK_SCHEMES):
        return value
    return ""


def safe_image_src(raw: str | None) -> str:
    """Return `raw` if it is a safe image source, else "".

    Allows http/https and relative URLs; rejects data:, javascript:, and any
    other scheme. Returns the *unescaped* value — callers HTML-escape it.
    """
    value = (raw or "").strip()
    if not value:
        return ""
    if not _has_scheme(value):
        return value
    if value.lower().startswith(_SAFE_IMAGE_SCHEMES):
        return value
    return ""
