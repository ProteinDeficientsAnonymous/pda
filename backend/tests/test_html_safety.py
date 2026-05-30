"""Unit tests for the URL-scheme allowlist helpers (_html_safety).

These cover the standalone defense layer directly, independent of the
ProseMirror/Delta renderers that consume it.
"""

import pytest
from community._html_safety import safe_image_src, safe_link_href


class TestSafeLinkHref:
    @pytest.mark.parametrize(
        "raw",
        [
            "https://x.test/path",
            "http://x.test",
            "mailto:a@b.test",
            "/events/1",
            "#frag",
            "?q=1",
            "page",
        ],
    )
    def test_safe_values_pass_through(self, raw):
        assert safe_link_href(raw) == raw

    @pytest.mark.parametrize(
        "raw",
        [
            "javascript:alert(1)",
            "data:text/html,<script>",
            "vbscript:msgbox(1)",
        ],
    )
    def test_dangerous_schemes_rejected(self, raw):
        assert safe_link_href(raw) == ""

    @pytest.mark.parametrize(
        "raw",
        [
            "java\tscript:alert(1)",
            "java\nscript:alert(1)",
            "java\rscript:alert(1)",
            "java\x00script:alert(1)",
            "\x01javascript:alert(1)",
            "java\x7fscript:alert(1)",
            "  javascript:alert(1)",
        ],
    )
    def test_control_char_bypass_rejected(self, raw):
        # Browsers strip C0 controls / DEL / leading whitespace from href
        # values, collapsing these back to "javascript:". Must be rejected.
        assert safe_link_href(raw) == ""

    def test_none_and_empty(self):
        assert safe_link_href(None) == ""
        assert safe_link_href("") == ""
        assert safe_link_href("   ") == ""

    def test_control_chars_stripped_from_safe_url(self):
        # Embedded controls are removed; a still-safe scheme survives cleaned.
        assert safe_link_href("https://x\t.test/a") == "https://x.test/a"


class TestSafeImageSrc:
    @pytest.mark.parametrize(
        "raw",
        ["https://x.test/a.png", "http://x.test/a.png", "/static/a.png"],
    )
    def test_safe_values_pass_through(self, raw):
        assert safe_image_src(raw) == raw

    @pytest.mark.parametrize(
        "raw",
        [
            "data:image/png;base64,AAAA",
            "javascript:alert(1)",
        ],
    )
    def test_dangerous_schemes_rejected(self, raw):
        assert safe_image_src(raw) == ""

    @pytest.mark.parametrize(
        "raw",
        [
            "data\n:text/html,<script>",
            "da\tta:image/svg+xml,x",
            "\x00data:image/png;base64,AAAA",
            "java\tscript:alert(1)",
        ],
    )
    def test_control_char_bypass_rejected(self, raw):
        assert safe_image_src(raw) == ""

    def test_none_and_empty(self):
        assert safe_image_src(None) == ""
        assert safe_image_src("") == ""
