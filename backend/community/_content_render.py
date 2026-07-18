"""Shared rendering glue for ProseMirror JSON content (TipTap).

Save flow: an endpoint accepts a ProseMirror JSON string and writes:
    content: "" (legacy column, kept empty on new writes)
    content_pm: ProseMirror string
    content_html: rendered HTML, the canonical read source

Keep this helper thin — the endpoint still owns model lookup + permission checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from community._html_sanitize import sanitize_content_html
from community._prosemirror_html import prosemirror_to_html


@dataclass(frozen=True, slots=True)
class RenderedContent:
    """Return value from `render_content_payload`."""

    content: str
    content_pm: str
    content_html: str


def render_content_payload(*, prosemirror: str | None = None) -> RenderedContent:
    if prosemirror and prosemirror.strip():
        return RenderedContent(
            content="",
            content_pm=prosemirror,
            content_html=sanitize_content_html(prosemirror_to_html(prosemirror)),
        )
    return RenderedContent(content="", content_pm="", content_html="")
