"""Tests for the rendered-HTML sanitizer (nh3 chokepoint).

The Delta / ProseMirror renderers no longer validate URL schemes themselves;
`sanitize_content_html` is the single security boundary, applied in
`_content_render` to the renderers' output. These tests assert against that
boundary: dangerous schemes/tags/attributes are stripped, while the renderers'
legitimate vocabulary (alignment, CTA classes, http/https/mailto/relative URLs)
survives.
"""

import pytest
from community._html_sanitize import sanitize_content_html


class TestSchemeStripping:
    @pytest.mark.parametrize(
        "html",
        [
            '<a href="javascript:alert(1)">x</a>',
            '<a href="data:text/html,<script>">x</a>',
            '<a href="vbscript:msgbox(1)">x</a>',
        ],
    )
    def test_dangerous_link_scheme_dropped(self, html):
        result = sanitize_content_html(html)
        assert "javascript:" not in result
        assert "data:" not in result
        assert "vbscript:" not in result
        # The anchor survives but carries no href.
        assert "href=" not in result

    @pytest.mark.parametrize(
        "html",
        [
            '<img src="javascript:alert(1)">',
            '<img src="data:image/png;base64,AAAA">',
            '<img src="data:image/svg+xml,<svg onload=alert(1)>">',
        ],
    )
    def test_dangerous_image_scheme_dropped(self, html):
        result = sanitize_content_html(html)
        assert "javascript:" not in result
        assert "data:" not in result
        assert "src=" not in result

    @pytest.mark.parametrize(
        "raw_href",
        [
            "java&#9;script:alert(1)",  # tab entity
            "java&#10;script:alert(1)",  # newline entity
            "  javascript:alert(1)",
            "java\tscript:alert(1)",
        ],
    )
    def test_control_char_scheme_bypass_dropped(self, raw_href):
        # Browsers strip C0/whitespace from URL values, so "java\tscript:" would
        # resolve back to "javascript:". nh3 must reject these.
        result = sanitize_content_html(f'<a href="{raw_href}">x</a>')
        assert "javascript:" not in result.lower()


class TestSafeUrlsSurvive:
    def test_https_link_survives(self):
        result = sanitize_content_html('<a href="https://example.com/path">x</a>')
        assert 'href="https://example.com/path"' in result

    def test_mailto_link_survives(self):
        result = sanitize_content_html('<a href="mailto:a@b.test">x</a>')
        assert 'href="mailto:a@b.test"' in result

    def test_relative_link_survives(self):
        result = sanitize_content_html('<a href="/events/1">x</a>')
        assert 'href="/events/1"' in result

    def test_https_image_survives(self):
        result = sanitize_content_html('<img src="https://example.com/i.png">')
        assert 'src="https://example.com/i.png"' in result

    def test_uploaded_media_image_survives(self):
        # Uploaded images are served as relative /media/ URLs (no scheme).
        result = sanitize_content_html('<img src="/media/uploads/photo.jpg">')
        assert 'src="/media/uploads/photo.jpg"' in result


class TestTagAndAttributeStripping:
    def test_script_tag_removed(self):
        result = sanitize_content_html("<p>ok</p><script>alert(1)</script>")
        assert "<script" not in result
        assert "<p>ok</p>" in result

    def test_event_handler_attribute_removed(self):
        result = sanitize_content_html('<img src="https://x.test/a.png" onerror="alert(1)">')
        assert "onerror" not in result
        assert 'src="https://x.test/a.png"' in result

    def test_iframe_removed(self):
        result = sanitize_content_html('<iframe src="https://evil.test"></iframe>')
        assert "<iframe" not in result


class TestStyleAndClassConstraints:
    def test_text_align_survives(self):
        result = sanitize_content_html('<p style="text-align: center">hi</p>')
        assert "text-align:center" in result.replace(" ", "")

    def test_non_alignment_style_dropped(self):
        result = sanitize_content_html('<p style="position: absolute; text-align: center">hi</p>')
        assert "position" not in result
        assert "text-align:center" in result.replace(" ", "")

    def test_cta_classes_survive(self):
        html = '<a class="cta cta--primary" href="https://x.test" role="button">go</a>'
        result = sanitize_content_html(html)
        assert "cta--primary" in result
        assert 'role="button"' in result

    def test_arbitrary_class_dropped(self):
        result = sanitize_content_html('<a class="evil" href="https://x.test">x</a>')
        assert "evil" not in result


class TestRelInjection:
    def test_blank_target_link_gets_safe_rel(self):
        result = sanitize_content_html('<a href="https://x.test" target="_blank">x</a>')
        assert 'rel="noopener noreferrer"' in result
        assert 'target="_blank"' in result

    def test_rel_injected_even_without_target(self):
        # nh3 applies link_rel to every anchor; harmless and consistent.
        result = sanitize_content_html('<a href="https://x.test">x</a>')
        assert 'rel="noopener noreferrer"' in result


class TestEdgeCases:
    def test_empty_string(self):
        assert sanitize_content_html("") == ""

    def test_plain_text_preserved(self):
        assert sanitize_content_html("<p>hello world</p>") == "<p>hello world</p>"
