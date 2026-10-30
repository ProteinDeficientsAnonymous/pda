import copy
import json
from typing import Any

from community.content.html_sanitize import sanitize_content_html
from community.content.prosemirror_html import prosemirror_to_html
from community.models import SpeechTemplate
from community.speech.blanks import BLANKS, SpeechValues

_PLACEHOLDER = "____"


def _doc_content(pm_json: str) -> list[dict]:
    if not pm_json or not pm_json.strip():
        return []
    try:
        doc = json.loads(pm_json)
    except ValueError:
        return []
    if not isinstance(doc, dict) or doc.get("type") != "doc":
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
    blank = BLANKS.get(key)
    if blank is None:
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


def render_speech_html(template: SpeechTemplate, kind: str, values: SpeechValues) -> str:
    kind_pm = template.restaurant_pm if kind == "restaurant" else template.walk_pm
    content = copy.deepcopy(_doc_content(template.shared_pm) + _doc_content(kind_pm))
    filled = [_fill_node(node, values) for node in content]
    doc = {"type": "doc", "content": filled}
    return sanitize_content_html(prosemirror_to_html(json.dumps(doc)))
