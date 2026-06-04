"""Convert Quill Delta JSON to HTML for static rendering."""

import json
from html import escape

# Each line is (list_of_spans, line_attrs_dict)
# A span is (text_or_sentinel, attrs_dict)
_Line = tuple[list[tuple[str, dict]], dict]


def delta_to_html(delta_json: str) -> str:
    """Convert a Quill Delta JSON string to an HTML string.

    Returns an empty string for empty, blank, or malformed input.
    """
    if not delta_json or not delta_json.strip():
        return ""
    try:
        ops = json.loads(delta_json)
    except (json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(ops, list):
        return ""
    lines = _parse_ops(ops)
    return _render_lines(lines)


def _flush_line(current_spans: list, lines: list, line_attrs: dict) -> None:
    lines.append((list(current_spans), line_attrs))
    current_spans.clear()


def _parse_text_insert(insert: str, attrs: dict, current_spans: list, lines: list) -> None:
    """Split a text insert on newlines and populate spans/lines."""
    parts = insert.split("\n")
    line_attrs = attrs if insert == "\n" else {}
    for i, part in enumerate(parts):
        if part:
            current_spans.append((part, attrs))
        if i < len(parts) - 1:
            _flush_line(current_spans, lines, line_attrs)


def _parse_op(op: dict, current_spans: list, lines: list) -> None:
    """Process a single Delta op, appending to current_spans / lines in place."""
    insert = op.get("insert", "")
    attrs = op.get("attributes") or {}

    if isinstance(insert, dict):
        image_url = insert.get("image", "")
        if image_url:
            current_spans.append(("__image__", {"src": escape(image_url)}))
        return

    if isinstance(insert, str):
        _parse_text_insert(insert, attrs, current_spans, lines)


def _parse_ops(ops: list) -> list[_Line]:
    """Split Delta ops into a list of (spans, line_attrs) pairs."""
    lines: list[_Line] = []
    current_spans: list[tuple[str, dict]] = []

    for op in ops:
        if isinstance(op, dict):
            _parse_op(op, current_spans, lines)

    if current_spans:
        lines.append((current_spans, {}))

    return lines


def _render_list_block(lines: list[_Line], i: int, list_type: str) -> tuple[str, int]:
    """Render consecutive list items of the same type; return (html, new_index)."""
    tag = "ol" if list_type == "ordered" else "ul"
    items = []
    while i < len(lines) and lines[i][1].get("list") == list_type:
        item_spans, _ = lines[i]
        items.append(f"<li>{_render_spans(item_spans)}</li>")
        i += 1
    return f"<{tag}>{''.join(items)}</{tag}>", i


def _render_lines(lines: list[_Line]) -> str:
    html_parts: list[str] = []
    i = 0
    while i < len(lines):
        spans, line_attrs = lines[i]
        list_type = line_attrs.get("list")

        if list_type in ("ordered", "bullet"):
            block_html, i = _render_list_block(lines, i, list_type)
            html_parts.append(block_html)
            continue

        header_level = line_attrs.get("header")
        if header_level in (1, 2, 3):
            html_parts.append(f"<h{header_level}>{_render_spans(spans)}</h{header_level}>")
        elif not spans:
            html_parts.append("<p><br></p>")
        else:
            html_parts.append(f"<p>{_render_spans(spans)}</p>")
        i += 1

    return "".join(html_parts)


def _apply_inline_attrs(chunk: str, attrs: dict) -> str:
    """Wrap chunk in inline formatting tags based on attrs."""
    if attrs.get("bold"):
        chunk = f"<strong>{chunk}</strong>"
    if attrs.get("italic"):
        chunk = f"<em>{chunk}</em>"
    if attrs.get("underline"):
        chunk = f"<u>{chunk}</u>"
    if attrs.get("strike"):
        chunk = f"<s>{chunk}</s>"
    if attrs.get("code"):
        chunk = f"<code>{chunk}</code>"
    link = attrs.get("link")
    if link:
        chunk = f'<a href="{escape(link)}">{chunk}</a>'
    return chunk


def _render_spans(spans: list[tuple[str, dict]]) -> str:
    parts = []
    for text, attrs in spans:
        if text == "__image__":
            parts.append(f'<img src="{attrs.get("src", "")}">')
        else:
            parts.append(_apply_inline_attrs(escape(text), attrs))
    return "".join(parts)
