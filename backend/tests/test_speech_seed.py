import importlib
import json

import pytest
from community.models import SpeechTemplate
from community.speech._render import render_speech_html
from community.speech.seed import DEFAULT_OPEN_ROLES, default_template_docs, seed_default_template


def _reset(**fields):
    defaults = {"shared_pm": "", "walk_pm": "", "restaurant_pm": "", "open_roles": []}
    SpeechTemplate.objects.update_or_create(pk=1, defaults={**defaults, **fields})


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


def test_default_open_roles():
    assert DEFAULT_OPEN_ROLES == [
        "whatsapp moderators (our biggest need at the moment)",
        "someone to send out announcements",
        "event facilitators and planners",
    ]


@pytest.mark.django_db
def test_rendered_walk_speech_uses_walk_content_only():
    _reset()
    seed_default_template(SpeechTemplate)
    html = render_speech_html(SpeechTemplate.get(), "walk", {})
    assert "social means SLOW" in html
    assert "buffet" not in html


@pytest.mark.django_db
def test_rendered_restaurant_speech_uses_restaurant_content_only():
    _reset()
    seed_default_template(SpeechTemplate)
    html = render_speech_html(SpeechTemplate.get(), "restaurant", {"restaurant": "veggie place"})
    assert "buffet" in html
    assert "veggie place" in html
    assert "social means SLOW" not in html


@pytest.mark.django_db
def test_seed_populates_empty_template():
    _reset()
    seed_default_template(SpeechTemplate)
    template = SpeechTemplate.get()
    assert json.loads(template.shared_pm)["type"] == "doc"
    assert json.loads(template.walk_pm)["type"] == "doc"
    assert json.loads(template.restaurant_pm)["type"] == "doc"
    assert template.open_roles == DEFAULT_OPEN_ROLES


@pytest.mark.django_db
def test_seed_twice_keeps_admin_edits():
    _reset()
    seed_default_template(SpeechTemplate)
    template = SpeechTemplate.get()
    template.walk_pm = "edited"
    template.open_roles = ["my role"]
    template.save()
    seed_default_template(SpeechTemplate)
    template.refresh_from_db()
    assert template.walk_pm == "edited"
    assert template.open_roles == ["my role"]


@pytest.mark.django_db
def test_seed_skips_when_any_doc_present():
    _reset(shared_pm="custom")
    seed_default_template(SpeechTemplate)
    template = SpeechTemplate.get()
    assert template.shared_pm == "custom"
    assert template.walk_pm == ""


@pytest.mark.django_db
def test_seed_treats_whitespace_as_empty():
    _reset(shared_pm="  \n", walk_pm=" ")
    seed_default_template(SpeechTemplate)
    assert "social means SLOW" in SpeechTemplate.get().walk_pm


@pytest.mark.django_db
def test_seed_keeps_existing_open_roles():
    _reset(open_roles=["mine"])
    seed_default_template(SpeechTemplate)
    template = SpeechTemplate.get()
    assert template.open_roles == ["mine"]
    assert template.shared_pm


@pytest.mark.django_db
def test_migration_seeds_via_historical_model():
    from django.apps import apps

    _reset()
    migration = importlib.import_module("community.migrations.0128_seed_speech_template")
    migration._seed(apps, None)
    assert SpeechTemplate.get().open_roles == DEFAULT_OPEN_ROLES
