"""Unit tests for the Delta-to-HTML converter."""

import json

import pytest
from community._delta_html import delta_to_html


class TestDeltaToHtmlEdgeCases:
    def test_empty_string(self):
        assert delta_to_html("") == ""

    def test_blank_string(self):
        assert delta_to_html("   ") == ""

    def test_invalid_json(self):
        assert delta_to_html("not json") == ""

    def test_json_object_not_array(self):
        assert delta_to_html('{"insert": "hi"}') == ""

    def test_empty_array(self):
        assert delta_to_html("[]") == ""


class TestDeltaToHtmlBasic:
    def _delta(self, ops):
        return json.dumps(ops)

    def test_plain_text(self):
        delta = self._delta([{"insert": "Hello world\n"}])
        assert delta_to_html(delta) == "<p>Hello world</p>"

    def test_escapes_html_entities(self):
        delta = self._delta([{"insert": "<script>alert('xss')</script>\n"}])
        result = delta_to_html(delta)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_bold(self):
        delta = self._delta([{"insert": "bold", "attributes": {"bold": True}}, {"insert": "\n"}])
        assert "<strong>bold</strong>" in delta_to_html(delta)

    def test_italic(self):
        delta = self._delta(
            [{"insert": "italic", "attributes": {"italic": True}}, {"insert": "\n"}]
        )
        assert "<em>italic</em>" in delta_to_html(delta)

    def test_underline(self):
        delta = self._delta(
            [{"insert": "under", "attributes": {"underline": True}}, {"insert": "\n"}]
        )
        assert "<u>under</u>" in delta_to_html(delta)

    def test_strike(self):
        delta = self._delta(
            [{"insert": "strike", "attributes": {"strike": True}}, {"insert": "\n"}]
        )
        assert "<s>strike</s>" in delta_to_html(delta)

    def test_inline_code(self):
        delta = self._delta([{"insert": "code", "attributes": {"code": True}}, {"insert": "\n"}])
        assert "<code>code</code>" in delta_to_html(delta)

    def test_link(self):
        delta = self._delta(
            [
                {"insert": "click here", "attributes": {"link": "https://example.com"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert '<a href="https://example.com">click here</a>' in result

    def test_bold_and_italic_combined(self):
        delta = self._delta(
            [
                {"insert": "both", "attributes": {"bold": True, "italic": True}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert "<strong>" in result
        assert "<em>" in result
        assert "both" in result


class TestDeltaToHtmlBlocks:
    def _delta(self, ops):
        return json.dumps(ops)

    def test_header_1(self):
        delta = self._delta([{"insert": "Title"}, {"insert": "\n", "attributes": {"header": 1}}])
        assert delta_to_html(delta) == "<h1>Title</h1>"

    def test_header_2(self):
        delta = self._delta([{"insert": "Sub"}, {"insert": "\n", "attributes": {"header": 2}}])
        assert delta_to_html(delta) == "<h2>Sub</h2>"

    def test_header_3(self):
        delta = self._delta([{"insert": "Minor"}, {"insert": "\n", "attributes": {"header": 3}}])
        assert delta_to_html(delta) == "<h3>Minor</h3>"

    def test_unordered_list(self):
        delta = self._delta(
            [
                {"insert": "Apple"},
                {"insert": "\n", "attributes": {"list": "bullet"}},
                {"insert": "Banana"},
                {"insert": "\n", "attributes": {"list": "bullet"}},
            ]
        )
        result = delta_to_html(delta)
        assert result == "<ul><li>Apple</li><li>Banana</li></ul>"

    def test_ordered_list(self):
        delta = self._delta(
            [
                {"insert": "First"},
                {"insert": "\n", "attributes": {"list": "ordered"}},
                {"insert": "Second"},
                {"insert": "\n", "attributes": {"list": "ordered"}},
            ]
        )
        result = delta_to_html(delta)
        assert result == "<ol><li>First</li><li>Second</li></ol>"

    def test_blank_line_becomes_br(self):
        delta = self._delta([{"insert": "A\n\nB\n"}])
        result = delta_to_html(delta)
        assert "<p>A</p>" in result
        assert "<p><br></p>" in result
        assert "<p>B</p>" in result

    def test_image(self):
        delta = self._delta(
            [{"insert": {"image": "https://example.com/img.png"}}, {"insert": "\n"}]
        )
        result = delta_to_html(delta)
        assert '<img src="https://example.com/img.png">' in result

    def test_multi_paragraph(self):
        delta = self._delta(
            [
                {"insert": "First paragraph\n"},
                {"insert": "Second paragraph\n"},
            ]
        )
        result = delta_to_html(delta)
        assert "<p>First paragraph</p>" in result
        assert "<p>Second paragraph</p>" in result


class TestDeltaToHtmlUrlSchemes:
    def _delta(self, ops):
        return json.dumps(ops)

    def test_link_javascript_scheme_stripped(self):
        delta = self._delta(
            [
                {"insert": "click", "attributes": {"link": "javascript:alert(1)"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert "javascript:" not in result
        # No safe href => no anchor wrapper; text survives.
        assert "<a " not in result
        assert "click" in result

    def test_link_data_scheme_stripped(self):
        delta = self._delta(
            [
                {"insert": "x", "attributes": {"link": "data:text/html,<script>"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert "data:" not in result
        assert "<a " not in result

    def test_link_https_survives(self):
        delta = self._delta(
            [
                {"insert": "click here", "attributes": {"link": "https://example.com"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert '<a href="https://example.com">click here</a>' in result

    def test_link_mailto_survives(self):
        delta = self._delta(
            [
                {"insert": "mail", "attributes": {"link": "mailto:a@b.test"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert '<a href="mailto:a@b.test">mail</a>' in result

    def test_link_relative_survives(self):
        delta = self._delta(
            [
                {"insert": "go", "attributes": {"link": "/events/1"}},
                {"insert": "\n"},
            ]
        )
        result = delta_to_html(delta)
        assert '<a href="/events/1">go</a>' in result

    def test_image_javascript_src_stripped(self):
        delta = self._delta([{"insert": {"image": "javascript:alert(1)"}}, {"insert": "\n"}])
        result = delta_to_html(delta)
        assert "javascript:" not in result
        # Unsafe src => image dropped entirely.
        assert "<img" not in result

    def test_image_data_src_stripped(self):
        delta = self._delta([{"insert": {"image": "data:image/png;base64,AAAA"}}, {"insert": "\n"}])
        result = delta_to_html(delta)
        assert "data:" not in result
        assert "<img" not in result

    def test_image_https_survives(self):
        delta = self._delta(
            [{"insert": {"image": "https://example.com/img.png"}}, {"insert": "\n"}]
        )
        result = delta_to_html(delta)
        assert '<img src="https://example.com/img.png">' in result

    @pytest.mark.parametrize(
        "raw",
        [
            "java\tscript:alert(1)",
            "java\nscript:alert(1)",
            "java\rscript:alert(1)",
            "java\x00script:alert(1)",
            "  javascript:alert(1)",
        ],
    )
    def test_link_control_char_scheme_bypass_stripped(self, raw):
        # Browsers strip these chars, resolving "java\tscript:" back to
        # "javascript:". The renderer must reject them.
        delta = self._delta([{"insert": "x", "attributes": {"link": raw}}, {"insert": "\n"}])
        result = delta_to_html(delta)
        assert "javascript:" not in result
        assert "<a " not in result

    @pytest.mark.parametrize(
        "raw",
        [
            "data\n:text/html,<script>",
            "da\tta:image/svg+xml,x",
            "\x00data:image/png;base64,AAAA",
        ],
    )
    def test_image_control_char_scheme_bypass_stripped(self, raw):
        delta = self._delta([{"insert": {"image": raw}}, {"insert": "\n"}])
        result = delta_to_html(delta)
        assert "data:" not in result
        assert "<img" not in result
