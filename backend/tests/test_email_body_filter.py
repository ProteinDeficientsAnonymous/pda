from notifications.templatetags.email_format import email_body


class TestEmailBodyFilter:
    def test_links_are_anchored_and_brand_styled_inline(self):
        html = email_body("join us at https://chat.whatsapp.com/abc123")
        assert 'href="https://chat.whatsapp.com/abc123"' in html
        assert 'style="color: #3c6939;"' in html

    def test_paragraphs_carry_explicit_margins(self):
        html = email_body("first para\n\nsecond para")
        assert html.count('<p style="margin: 0 0 16px;">') == 2
        assert "<p>" not in html

    def test_single_newlines_become_breaks(self):
        html = email_body("line one\nline two")
        assert "<br>" in html

    def test_markup_in_the_body_is_escaped(self):
        html = email_body("hi <script>alert(1)</script> & welcome")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&amp; welcome" in html

    def test_raw_markup_cannot_inject_live_attributes(self):
        """Escaping runs before styling, so a vetter's tag becomes text.

        The bare url inside it is still auto-linked — that is the point of
        urlize — but the tag they typed carries none of its own attributes.
        """
        html = email_body('<a href="https://x.example.com" onclick="steal()">click</a>')
        assert "&lt;a href=" in html
        assert 'onclick="steal()"' not in html

    def test_generated_anchors_are_nofollow(self):
        html = email_body("see https://chat.whatsapp.com/abc123")
        assert html.count("<a ") == html.count('rel="nofollow"')
