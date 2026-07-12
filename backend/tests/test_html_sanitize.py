"""Tests for the rendered-HTML sanitizer (`sanitize_content_html`)."""

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
        # Browsers strip C0/whitespace from URLs, so "java\tscript:" resolves back
        # to "javascript:"; the whole href must be dropped, not merely mangled.
        result = sanitize_content_html(f'<a href="{raw_href}">x</a>')
        assert "javascript:" not in result.lower()
        assert "href=" not in result

    def test_protocol_relative_link_dropped(self):
        result = sanitize_content_html('<a href="//evil.com">x</a>')
        assert "evil.com" not in result
        assert "href=" not in result

    def test_protocol_relative_image_dropped(self):
        result = sanitize_content_html('<img src="//evil.com/x.png">')
        assert "evil.com" not in result
        assert "src=" not in result

    @pytest.mark.parametrize(
        "raw_href",
        [
            "/\\evil.com",  # backslash — browsers normalise /\ to //
            "\\\\evil.com",  # double backslash
            "/\\/evil.com",  # mixed
            " //evil.com",  # leading space
            "\t//evil.com",  # leading tab
            "\n//evil.com",  # leading newline
            "/\t/evil.com",  # tab BETWEEN the slashes (browsers strip it -> //)
            "/\t\t/evil.com",  # multiple embedded tabs
            "/\n/evil.com",  # embedded newline
            "/\r/evil.com",  # embedded CR (html5ever folds to \n, still stripped)
            "///evil.com",  # 3+ leading slashes — browsers read authority
            "////evil.com",  # 4 leading slashes
            "//[evil.com",  # malformed IPv6 — urlsplit raises, must fail closed
            "//[::1",  # unterminated IPv6 literal
        ],
    )
    def test_protocol_relative_bypass_variants_dropped(self, raw_href):
        # Each obfuscation resolves to //evil.com in a browser; _normalize_url must
        # canonicalise before the protocol-relative check so every variant drops.
        result = sanitize_content_html(f'<a href="{raw_href}">x</a>')
        assert "evil.com" not in result
        assert "href=" not in result

    def test_embedded_control_scheme_url_canonicalised(self):
        result = sanitize_content_html('<a href="https:/\t/evil.com">x</a>')
        assert 'href="https://evil.com"' in result
        assert "\t" not in result

    def test_legit_query_backslash_preserved(self):
        # Backslash folding applies only to the authority/path — a query backslash
        # is legitimate and must survive.
        result = sanitize_content_html('<a href="https://good.com/p?x=a\\b">y</a>')
        assert "x=a\\b" in result

    def test_backslash_obfuscated_scheme_url_canonicalised(self):
        result = sanitize_content_html('<a href="https:/\\evil.com">x</a>')
        assert 'href="https://evil.com"' in result
        assert "\\" not in result

    def test_mailto_image_src_dropped(self):
        result = sanitize_content_html('<img src="mailto:a@b.test">')
        assert "mailto:" not in result
        assert "src=" not in result


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

    def test_text_align_case_insensitive(self):
        for raw in ("TEXT-ALIGN: center", "text-align: CENTER", "Text-Align: Center"):
            result = sanitize_content_html(f'<p style="{raw}">hi</p>')
            assert "text-align:center" in result.replace(" ", "").lower()

    def test_non_alignment_style_dropped(self):
        result = sanitize_content_html('<p style="position: absolute; text-align: center">hi</p>')
        assert "position" not in result
        assert "text-align:center" in result.replace(" ", "")

    @pytest.mark.parametrize(
        "bad_value",
        [
            "behavior(url(x.htc))",  # legacy-IE behavior() CSS
            "expression(alert(1))",  # legacy-IE expression() CSS
            "-webkit-center",  # not in the renderers' vocabulary
            "justify",  # frontend-only; renderers never emit it
            "red",  # arbitrary garbage value
        ],
    )
    def test_malicious_text_align_value_dropped(self, bad_value):
        result = sanitize_content_html(f'<p style="text-align: {bad_value}">hi</p>')
        assert "style=" not in result
        assert bad_value.split("(")[0] not in result

    def test_prefixed_text_align_property_dropped(self):
        result = sanitize_content_html('<p style="-webkit-text-align: right">hi</p>')
        assert "style=" not in result

    def test_text_align_preserved_when_mixed_with_malicious_sibling(self):
        # Keep the valid alignment while stripping an adjacent injection.
        result = sanitize_content_html(
            '<p style="text-align: center; position: fixed; top: 0">hi</p>'
        )
        assert "text-align:center" in result.replace(" ", "")
        assert "position" not in result
        assert "fixed" not in result

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
        result = sanitize_content_html('<a href="https://x.test">x</a>')
        assert 'rel="noopener noreferrer"' in result


class TestRendererRoundTrip:
    """Feeds real renderer output through the sanitizer to catch allowlist drift."""

    def test_prosemirror_full_document_survives(self):
        import json

        from community._prosemirror_html import prosemirror_to_html

        pm = json.dumps(
            {
                "type": "doc",
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": 2, "textAlign": "center"},
                        "content": [{"type": "text", "text": "Title"}],
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
                            {
                                "type": "text",
                                "text": " link",
                                "marks": [{"type": "link", "attrs": {"href": "https://x.test"}}],
                            },
                        ],
                    },
                    {
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "item"}],
                                    }
                                ],
                            }
                        ],
                    },
                    {"type": "image", "attrs": {"src": "/media/p.jpg"}},
                    {
                        "type": "cta",
                        "attrs": {"href": "https://x.test", "label": "Go", "variant": "primary"},
                    },
                ],
            }
        )
        result = sanitize_content_html(prosemirror_to_html(pm))
        assert '<h2 style="text-align: center">Title</h2>' in result
        assert "<strong>bold</strong>" in result
        assert '<a href="https://x.test"' in result
        assert "<ul><li>item</li></ul>" in result
        assert '<img src="/media/p.jpg">' in result
        assert 'class="cta cta--primary"' in result
        assert 'role="button"' in result
        assert 'target="_blank"' in result

    def test_delta_document_survives(self):
        import json

        from community._delta_html import delta_to_html

        delta = json.dumps(
            [
                {"insert": "hi "},
                {"insert": "bold", "attributes": {"bold": True}},
                {"insert": " "},
                {"insert": "lnk", "attributes": {"link": "https://x.test"}},
                {"insert": "\n"},
            ]
        )
        result = sanitize_content_html(delta_to_html(delta))
        assert "<strong>bold</strong>" in result
        assert '<a href="https://x.test"' in result
        assert "hi " in result


class TestEdgeCases:
    def test_empty_string(self):
        assert sanitize_content_html("") == ""

    def test_plain_text_preserved(self):
        assert sanitize_content_html("<p>hello world</p>") == "<p>hello world</p>"
