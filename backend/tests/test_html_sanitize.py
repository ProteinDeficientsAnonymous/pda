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
        # The whole href must be dropped, not merely mangled — a surviving
        # href="java\tscript:" still executes in a browser.
        assert "href=" not in result

    def test_protocol_relative_link_dropped(self):
        # "//evil.com" carries no scheme, so the url_schemes allowlist never
        # rejects it; _attribute_filter must, or it resolves to https://evil.com.
        result = sanitize_content_html('<a href="//evil.com">x</a>')
        assert "evil.com" not in result
        assert "href=" not in result

    def test_protocol_relative_image_dropped(self):
        # A protocol-relative image src is an attacker-controlled remote load
        # (tracking pixel / IP leak) that bypasses the scheme allowlist.
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
        ],
    )
    def test_protocol_relative_bypass_variants_dropped(self, raw_href):
        # The literal-"//" check is not enough: browsers ignore leading
        # whitespace/controls and treat "\" as "/", so each of these resolves to
        # //evil.com. _normalize_url must canonicalise before the check.
        # (A leading NUL is NOT included: html5ever rewrites it to U+FFFD at
        # parse time, which makes the URL a same-origin relative path, not
        # protocol-relative — so it is already inert.)
        result = sanitize_content_html(f'<a href="{raw_href}">x</a>')
        assert "evil.com" not in result
        assert "href=" not in result

    def test_backslash_obfuscated_scheme_url_canonicalised(self):
        # "https:/\evil.com" has an allowed scheme and no literal "//", but a
        # browser resolves it to https://evil.com. Canonicalise it so the stored
        # value is unambiguous rather than a parser-differential trap.
        result = sanitize_content_html('<a href="https:/\\evil.com">x</a>')
        assert 'href="https://evil.com"' in result
        assert "\\" not in result

    def test_mailto_image_src_dropped(self):
        # mailto: is valid for links but inert/pointless on an image src; the
        # image scheme guard is http/https only.
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

    def test_text_align_case_insensitive(self):
        # The property name match is case-insensitive (matching the frontend's
        # /i flag), so an upper/mixed-case property is preserved, not dropped.
        result = sanitize_content_html('<p style="TEXT-ALIGN: center">hi</p>')
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
        # nh3's filter_style_properties keeps the *property* but not the *value*,
        # so _attribute_filter must reject any value outside left/center/right
        # (mirroring the frontend's ALLOWED_TEXT_ALIGN).
        result = sanitize_content_html(f'<p style="text-align: {bad_value}">hi</p>')
        assert "style=" not in result
        assert bad_value.split("(")[0] not in result

    def test_text_align_preserved_when_mixed_with_malicious_sibling(self):
        # The security-critical branch: keep the valid alignment while stripping
        # an adjacent injection, rather than dropping the whole attribute.
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
        # nh3 applies link_rel to every anchor; harmless and consistent.
        result = sanitize_content_html('<a href="https://x.test">x</a>')
        assert 'rel="noopener noreferrer"' in result


class TestRendererRoundTrip:
    """Guards the module's core invariant: the allowlist exactly covers what the
    renderers emit. These feed real renderer output through the sanitizer, so if
    a renderer starts emitting a tag/attr/class the allowlist omits, sanitization
    silently strips it and one of these fails — catching drift the hand-written
    literals above cannot.
    """

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
        # Nothing the renderer emitted is stripped (rel injection / attr reorder
        # aside, which is why this asserts on fragments rather than equality).
        assert '<h2 style="text-align: center">Title</h2>' in result
        assert "<strong>bold</strong>" in result
        assert '<a href="https://x.test"' in result
        assert "<ul><li>item</li></ul>" in result
        assert '<img src="/media/p.jpg">' in result
        assert 'class="cta cta--primary"' in result
        assert 'role="button"' in result
        # The CTA opens in a new tab; pin target so an allowlist edit dropping
        # it (which would also moot the rel-injection guard) fails this test.
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
