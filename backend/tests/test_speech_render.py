import json

import pytest
from community.content.html_sanitize import sanitize_content_html
from community.content.prosemirror_html import prosemirror_to_html
from community.models import SpeechTemplate
from community.speech._render import render_speech_html
from community.speech.blanks import BLANKS, clean_values


def _text(value):
    return {"type": "text", "text": value}


def _blank(key):
    return {"type": "speechBlank", "attrs": {"key": key}}


def _para(*inline):
    return {"type": "paragraph", "content": list(inline)}


def _doc(*blocks):
    return json.dumps({"type": "doc", "content": list(blocks)})


def _template(shared=(), walk=(), restaurant=()):
    return SpeechTemplate(
        shared_pm=_doc(*shared) if shared else "",
        walk_pm=_doc(*walk) if walk else "",
        restaurant_pm=_doc(*restaurant) if restaurant else "",
    )


class TestKindSelection:
    def test_walk_includes_walk_text_only(self):
        t = _template(
            shared=[_para(_text("shared line"))],
            walk=[_para(_text("walk line"))],
            restaurant=[_para(_text("restaurant line"))],
        )
        html = render_speech_html(t, "walk", {})
        assert "shared line" in html
        assert "walk line" in html
        assert "restaurant line" not in html

    def test_restaurant_includes_restaurant_text_only(self):
        t = _template(
            shared=[_para(_text("shared line"))],
            walk=[_para(_text("walk line"))],
            restaurant=[_para(_text("restaurant line"))],
        )
        html = render_speech_html(t, "restaurant", {})
        assert "shared line" in html
        assert "restaurant line" in html
        assert "walk line" not in html

    def test_empty_template_renders_empty(self):
        assert render_speech_html(SpeechTemplate(), "walk", {}) == ""


class TestSingleBlank:
    def test_inline_value_substituted(self):
        t = _template(
            shared=[_para(_text("today our facilitators are "), _blank("facilitators"), _text("."))]
        )
        html = render_speech_html(t, "walk", {"facilitators": "maya, sam"})
        assert html == "<p>today our facilitators are maya, sam.</p>"

    @pytest.mark.parametrize("values", [{}, {"facilitators": ""}])
    def test_empty_or_missing_value_shows_placeholder(self, values):
        t = _template(shared=[_para(_text("by "), _blank("facilitators"))])
        assert render_speech_html(t, "walk", values) == "<p>by ____</p>"

    def test_unknown_key_shows_placeholder(self):
        t = _template(shared=[_para(_blank("nope"))])
        assert render_speech_html(t, "walk", {}) == "<p>____</p>"

    def test_value_is_escaped(self):
        t = _template(walk=[_para(_blank("walk_details"))])
        html = render_speech_html(t, "walk", {"walk_details": "<img src=x onerror=alert(1)>"})
        assert "&lt;img" in html
        assert "<img" not in html


class TestStructure:
    def test_blockquote_passes_through(self):
        t = _template(shared=[{"type": "blockquote", "content": [_para(_text("speaker note"))]}])
        assert "<blockquote>" in render_speech_html(t, "walk", {})

    def test_blank_inside_blockquote_is_filled(self):
        quote = {"type": "blockquote", "content": [_para(_text("ask: "), _blank("intro_question"))]}
        html = render_speech_html(_template(shared=[quote]), "walk", {"intro_question": "why?"})
        assert html == "<blockquote><p>ask: why?</p></blockquote>"

    def test_template_is_not_mutated(self):
        t = _template(shared=[_para(_text("hi "), _blank("facilitators"))])
        before = (t.shared_pm, t.walk_pm, t.restaurant_pm)
        render_speech_html(t, "walk", {"facilitators": "sam"})
        assert (t.shared_pm, t.walk_pm, t.restaurant_pm) == before

    @pytest.mark.parametrize("raw", ["   ", "not json", '{"type":"nope"}'])
    def test_bad_stored_docs_treated_as_empty(self, raw):
        t = SpeechTemplate(shared_pm=raw, walk_pm=raw, restaurant_pm=raw)
        assert render_speech_html(t, "walk", {}) == ""


class TestBlankPreview:
    def test_blank_renders_label_span_and_survives_sanitizer(self):
        html = prosemirror_to_html(_doc(_para(_blank("walk_details"))))
        assert html == '<p><span class="speech-blank">walk details</span></p>'
        assert sanitize_content_html(html) == html

    def test_unknown_blank_key_renders_nothing(self):
        assert prosemirror_to_html(_doc(_para(_blank("nope")))) == "<p><br></p>"

    def test_every_blank_label_renders(self):
        for key, blank in BLANKS.items():
            assert blank.label in prosemirror_to_html(_doc(_para(_blank(key))))


class TestCleanValues:
    def test_drops_unknown_keys(self):
        assert clean_values({"bogus": "x"}) == {}

    def test_keeps_valid_values(self):
        raw = {"facilitators": "sam", "open_roles": ["a", "b"], "bogus": 1}
        assert clean_values(raw) == {"facilitators": "sam", "open_roles": ["a", "b"]}

    def test_wrong_type_raises_even_with_unknown_keys(self):
        with pytest.raises(ValueError, match="open_roles"):
            clean_values({"bogus": "x", "open_roles": "notalist"})

    def test_string_blank_rejects_list(self):
        with pytest.raises(ValueError, match="facilitators"):
            clean_values({"facilitators": ["a"]})

    def test_list_items_must_be_strings(self):
        with pytest.raises(ValueError):
            clean_values({"open_roles": [1]})

    def test_string_length_limit(self):
        assert clean_values({"facilitators": "x" * 2000})
        with pytest.raises(ValueError):
            clean_values({"facilitators": "x" * 2001})

    def test_list_count_limit(self):
        assert clean_values({"open_roles": ["a"] * 20})
        with pytest.raises(ValueError):
            clean_values({"open_roles": ["a"] * 21})

    def test_list_item_length_limit(self):
        assert clean_values({"open_roles": ["x" * 300]})
        with pytest.raises(ValueError):
            clean_values({"open_roles": ["x" * 301]})
