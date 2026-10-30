import json

import pytest
from community.content.html_sanitize import sanitize_content_html
from community.content.prosemirror_html import prosemirror_to_html
from community.speech.blanks import BLANKS, clean_values


def _blank(key):
    return {"type": "speechBlank", "attrs": {"key": key}}


def _para(*inline):
    return {"type": "paragraph", "content": list(inline)}


def _doc(*blocks):
    return json.dumps({"type": "doc", "content": list(blocks)})


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
