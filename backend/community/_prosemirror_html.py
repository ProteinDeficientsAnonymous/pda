"""Convert ProseMirror JSON (emitted by TipTap) to HTML for static rendering.

Mirrors _delta_html.py intentionally — the narrow feature set the app uses
(bold/italic/underline/strike/code/link inlines; h1–h3 headings; ol/ul lists;
images; paragraphs) maps 1:1 between the two editor formats. Keeping a
single HTML output shape means view-mode consumers (Flutter app, anon web
viewers) don't care which editor produced the document.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any


def prosemirror_to_html(pm_json: str) -> str:
    """Convert a TipTap/ProseMirror JSON string to HTML.

    Empty, blank, or malformed input returns "".
    """
    if not pm_json or not pm_json.strip():
        return ""
    try:
        doc = json.loads(pm_json)
    except (json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        return ""
    return _render_nodes(doc.get("content") or [])


def _render_nodes(nodes: list[Any]) -> str:
    return "".join(_render_node(n) for n in nodes if isinstance(n, dict))


def _render_paragraph(content: list[Any], _attrs: dict) -> str:
    inner = _render_inline(content)
    return f"<p>{inner}</p>" if inner else "<p><br></p>"


def _render_heading(content: list[Any], attrs: dict) -> str:
    level = attrs.get("level", 1)
    if level not in (1, 2, 3):
        level = 1
    return f"<h{level}>{_render_inline(content)}</h{level}>"


def _render_list_item(content: list[Any], _attrs: dict) -> str:
    # A listItem's content is block nodes (usually one paragraph). Inline the
    # paragraph's text into the <li> so HTML matches the Delta renderer.
    if len(content) == 1 and isinstance(content[0], dict) and content[0].get("type") == "paragraph":
        return f"<li>{_render_inline(content[0].get('content') or [])}</li>"
    return f"<li>{_render_nodes(content)}</li>"


_BLOCK_RENDERERS = {
    "paragraph": _render_paragraph,
    "heading": _render_heading,
    "bulletList": lambda c, _a: f"<ul>{_render_nodes(c)}</ul>",
    "orderedList": lambda c, _a: f"<ol>{_render_nodes(c)}</ol>",
    "listItem": _render_list_item,
    "blockquote": lambda c, _a: f"<blockquote>{_render_nodes(c)}</blockquote>",
    "horizontalRule": lambda _c, _a: "<hr>",
    "hardBreak": lambda _c, _a: "<br>",
    "image": lambda _c, a: f'<img src="{escape(a.get("src", ""))}">',
}


def _render_node(node: dict) -> str:
    renderer = _BLOCK_RENDERERS.get(node.get("type", ""))
    if renderer is None:
        return ""
    return renderer(node.get("content") or [], node.get("attrs") or {})


def _render_inline(nodes: list[Any]) -> str:
    parts: list[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        t = n.get("type")
        if t == "text":
            parts.append(_apply_marks(escape(n.get("text", "")), n.get("marks") or []))
        elif t == "hardBreak":
            parts.append("<br>")
        elif t == "image":
            src = (n.get("attrs") or {}).get("src", "")
            parts.append(f'<img src="{escape(src)}">')
    return "".join(parts)


def _apply_marks(chunk: str, marks: list[Any]) -> str:
    # Order matches _delta_html.py so the HTML output is identical for
    # equivalent documents.
    has = {m.get("type"): m for m in marks if isinstance(m, dict)}
    if "bold" in has:
        chunk = f"<strong>{chunk}</strong>"
    if "italic" in has:
        chunk = f"<em>{chunk}</em>"
    if "underline" in has:
        chunk = f"<u>{chunk}</u>"
    if "strike" in has:
        chunk = f"<s>{chunk}</s>"
    if "code" in has:
        chunk = f"<code>{chunk}</code>"
    if "link" in has:
        href = ((has["link"].get("attrs") or {}).get("href")) or ""
        chunk = f'<a href="{escape(href)}">{chunk}</a>'
    return chunk
