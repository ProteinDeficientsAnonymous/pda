"""Shared rendering glue for dual-format content (Quill Delta ↔ ProseMirror JSON).

Save flow: an endpoint accepts either a Delta string (from Flutter) or a
ProseMirror JSON string (from React/TipTap), and writes:
    content: Delta string (may stay empty if the writer sent PM)
    content_pm: ProseMirror string (may stay empty if the writer sent Delta)
    content_html: rendered HTML, the canonical read source

Keep this helper thin — the endpoint still owns model lookup + permission checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from community._delta_html import delta_to_html
from community._prosemirror_html import prosemirror_to_html


@dataclass(frozen=True, slots=True)
class RenderedContent:
    """Return value from `render_content_payload`.

    Always includes all three fields so model writes can use setattr in a loop.
    Only the non-empty fields need to be written, but keeping them addressable
    by attribute lets callers pick what they save.
    """

    content: str  # Delta JSON string (Flutter format)
    content_pm: str  # ProseMirror JSON string (TipTap format)
    content_html: str  # rendered HTML


def render_content_payload(
    *, delta: str | None = None, prosemirror: str | None = None
) -> RenderedContent:
    """Render HTML from whichever format the client provided.

    If both are provided, ProseMirror wins (matches the order TipTap should
    appear in the payload path). Callers on the write path should pass the
    format the client actually sent; the one that's missing will be stored
    as "" on the model.
    """
    if prosemirror and prosemirror.strip():
        return RenderedContent(
            content="",
            content_pm=prosemirror,
            content_html=prosemirror_to_html(prosemirror),
        )
    if delta and delta.strip():
        return RenderedContent(
            content=delta,
            content_pm="",
            content_html=delta_to_html(delta),
        )
    return RenderedContent(content="", content_pm="", content_html="")
