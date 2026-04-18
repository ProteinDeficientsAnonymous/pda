"""Tests for ProseMirror JSON → HTML rendering."""

import pytest
from community._prosemirror_html import prosemirror_to_html


@pytest.fixture
def edit_homepage_headers(db):
    from ninja_jwt.tokens import RefreshToken
    from users.models import Role, User
    from users.permissions import PermissionKey

    user = User.objects.create_user(
        phone_number="+12025550999",
        password="testpass",
        display_name="PM Editor",
    )
    role = Role.objects.create(
        name="pm_homepage_editor",
        permissions=[PermissionKey.EDIT_HOMEPAGE],
    )
    user.roles.add(role)
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _doc(*children):
    return '{"type":"doc","content":' + "[" + ",".join(children) + "]}"


def _para(*inline):
    return '{"type":"paragraph","content":[' + ",".join(inline) + "]}"


def _text(value, *marks):
    marks_json = "[" + ",".join(f'{{"type":"{m}"}}' for m in marks) + "]"
    return f'{{"type":"text","text":"{value}","marks":{marks_json}}}'


class TestEmpty:
    def test_empty_string(self):
        assert prosemirror_to_html("") == ""

    def test_blank_string(self):
        assert prosemirror_to_html("   ") == ""

    def test_malformed_json(self):
        assert prosemirror_to_html("not json") == ""

    def test_non_doc_root(self):
        assert prosemirror_to_html('{"type":"paragraph"}') == ""


class TestParagraphs:
    def test_plain_text(self):
        html = prosemirror_to_html(_doc(_para(_text("hello"))))
        assert html == "<p>hello</p>"

    def test_empty_paragraph(self):
        html = prosemirror_to_html('{"type":"doc","content":[{"type":"paragraph"}]}')
        assert html == "<p><br></p>"

    def test_html_escapes(self):
        html = prosemirror_to_html(_doc(_para(_text("<script>alert(1)</script>"))))
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestInlineMarks:
    def test_bold(self):
        html = prosemirror_to_html(_doc(_para(_text("bold", "bold"))))
        assert html == "<p><strong>bold</strong></p>"

    def test_italic(self):
        html = prosemirror_to_html(_doc(_para(_text("it", "italic"))))
        assert html == "<p><em>it</em></p>"

    def test_multiple_marks_combined(self):
        html = prosemirror_to_html(_doc(_para(_text("both", "bold", "italic"))))
        assert html == "<p><em><strong>both</strong></em></p>"

    def test_code(self):
        html = prosemirror_to_html(_doc(_para(_text("x()", "code"))))
        assert html == "<p><code>x()</code></p>"

    def test_link(self):
        pm = (
            '{"type":"doc","content":[{"type":"paragraph","content":['
            '{"type":"text","text":"click","marks":[{"type":"link","attrs":{"href":"https://x.test"}}]}]}]}'
        )
        html = prosemirror_to_html(pm)
        assert html == '<p><a href="https://x.test">click</a></p>'


class TestHeadings:
    def test_heading_level(self):
        pm = (
            '{"type":"doc","content":[{"type":"heading","attrs":{"level":2},"content":['
            '{"type":"text","text":"h2"}]}]}'
        )
        assert prosemirror_to_html(pm) == "<h2>h2</h2>"

    def test_clamped_level(self):
        pm = (
            '{"type":"doc","content":[{"type":"heading","attrs":{"level":7},"content":['
            '{"type":"text","text":"x"}]}]}'
        )
        assert prosemirror_to_html(pm) == "<h1>x</h1>"


class TestLists:
    def test_bullet_list(self):
        pm = (
            '{"type":"doc","content":[{"type":"bulletList","content":['
            '{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"a"}]}]},'
            '{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"b"}]}]}'
            "]}]}"
        )
        assert prosemirror_to_html(pm) == "<ul><li>a</li><li>b</li></ul>"

    def test_ordered_list(self):
        pm = (
            '{"type":"doc","content":[{"type":"orderedList","content":['
            '{"type":"listItem","content":[{"type":"paragraph","content":[{"type":"text","text":"1"}]}]}'
            "]}]}"
        )
        assert prosemirror_to_html(pm) == "<ol><li>1</li></ol>"


class TestImages:
    def test_block_image(self):
        pm = '{"type":"doc","content":[{"type":"image","attrs":{"src":"https://x.test/a.png"}}]}'
        assert prosemirror_to_html(pm) == '<img src="https://x.test/a.png">'

    def test_image_src_escaped(self):
        pm = '{"type":"doc","content":[{"type":"image","attrs":{"src":"a\\"b"}}]}'
        html = prosemirror_to_html(pm)
        # src is escaped as an HTML attribute value
        assert 'src="a&quot;b"' in html


@pytest.mark.django_db
class TestDualFormatEndpoint:
    """End-to-end: posting content_pm produces HTML identical in spirit to
    posting the equivalent Delta. Dual-format keeps React (TipTap) and Flutter
    (Quill) writing compatible rows."""

    def test_home_accepts_content_pm(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content_pm": _doc(_para(_text("hi")))},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content_pm"] != ""
        assert data["content"] == ""
        assert data["content_html"] == "<p>hi</p>"

    def test_home_still_accepts_content_delta(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content": '[{"insert":"hi\\n"}]'},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] != ""
        assert data["content_pm"] == ""
        assert "<p>hi</p>" in data["content_html"]

    def test_home_pm_then_delta_overwrites(self, api_client, edit_homepage_headers):
        # Write PM, then overwrite with Delta — content_pm should clear so the
        # row reflects only the latest writer's format (no stale cross-format
        # leftovers).
        api_client.patch(
            "/api/community/home/",
            {"content_pm": _doc(_para(_text("first")))},
            content_type="application/json",
            **edit_homepage_headers,
        )
        response = api_client.patch(
            "/api/community/home/",
            {"content": '[{"insert":"second\\n"}]'},
            content_type="application/json",
            **edit_homepage_headers,
        )
        data = response.json()
        assert data["content_pm"] == ""
        assert data["content"] != ""
        assert "second" in data["content_html"]
        assert "first" not in data["content_html"]
