from typing import Any

from community.content.html_sanitize import sanitize_content_html
from community.content.prosemirror_html import parse_prosemirror_doc, render_nodes
from community.models import EventFormat, SpeechTemplate
from community.speech.blanks import BLANKS, SpeechValues

_PLACEHOLDER = "____"


def _doc_content(pm_json: str) -> list[dict]:
    doc = parse_prosemirror_doc(pm_json)
    if doc is None:
        return []
    return [n for n in (doc.get("content") or []) if isinstance(n, dict)]


def _is_blank(node: Any) -> bool:
    return isinstance(node, dict) and node.get("type") == "speechBlank"


def _blank_key(node: dict) -> str:
    return (node.get("attrs") or {}).get("key", "")


def _text_node(text: str) -> dict:
    return {"type": "text", "text": text}


def _inline_text(node: dict, values: SpeechValues) -> str:
    key = _blank_key(node)
    if key not in BLANKS:
        return _PLACEHOLDER
    value = values.get(key)
    return value if isinstance(value, str) and value else _PLACEHOLDER


def _fill_node(node: dict, values: SpeechValues) -> dict:
    children = node.get("content")
    if not isinstance(children, list):
        return node
    node["content"] = [
        _text_node(_inline_text(c, values)) if _is_blank(c) else _fill_node(c, values)
        for c in children
        if isinstance(c, dict)
    ]
    return node


def render_speech_html(template: SpeechTemplate, event_format: str, values: SpeechValues) -> str:
    format_pm = (
        template.restaurant_pm if event_format == EventFormat.RESTAURANT else template.walk_pm
    )
    content = _doc_content(template.shared_pm) + _doc_content(format_pm)
    filled = [_fill_node(node, values) for node in content]
    return sanitize_content_html(render_nodes(filled))
