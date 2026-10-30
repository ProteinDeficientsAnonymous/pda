import json

import pytest
from community.speech.seed import default_template_docs


def _walk(node):
    yield node
    for child in node.get("content") or []:
        yield from _walk(child)


def _blank_keys(doc):
    return {n["attrs"]["key"] for n in _walk(doc) if n.get("type") == "speechBlank"}


def _blockquote_texts(doc):
    return [
        "".join(t.get("text", "") for t in _walk(n) if t.get("type") == "text")
        for n in _walk(doc)
        if n.get("type") == "blockquote"
    ]


def _paragraphs_with_blank(doc, key):
    return [
        n
        for n in _walk(doc)
        if n.get("type") == "paragraph"
        and any(c.get("type") == "speechBlank" and c["attrs"]["key"] == key for c in n["content"])
    ]


def test_docs_are_valid_prosemirror_docs():
    for doc in default_template_docs():
        assert doc["type"] == "doc"
        assert doc["content"]
        json.dumps(doc)


def test_shared_doc_blanks():
    shared, _, _ = default_template_docs()
    assert {"facilitators", "open_roles", "upcoming_events"} <= _blank_keys(shared)


@pytest.mark.parametrize("key", ["open_roles", "upcoming_events"])
def test_list_blanks_sit_alone_in_their_paragraph(key):
    shared, _, _ = default_template_docs()
    paragraphs = _paragraphs_with_blank(shared, key)
    assert len(paragraphs) == 1
    assert len(paragraphs[0]["content"]) == 1


def test_walk_doc_blanks():
    _, walk, _ = default_template_docs()
    assert {"front_walker", "back_walker", "walk_details", "intro_question"} <= _blank_keys(walk)


def test_restaurant_doc_blanks():
    _, _, restaurant = default_template_docs()
    assert {"restaurant", "intro_question"} <= _blank_keys(restaurant)


def test_speaker_notes_are_blockquotes():
    shared, walk, restaurant = default_template_docs()
    assert len(_blockquote_texts(shared)) == 2
    assert any("count off" in t for t in _blockquote_texts(walk))
    notes = _blockquote_texts(restaurant)
    assert len(notes) == 3
    assert any("chaotic but the dust will settle" in t for t in notes)
