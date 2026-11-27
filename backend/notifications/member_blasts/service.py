import html as html_lib
import re
from typing import NamedTuple

from community.content.html_sanitize import sanitize_content_html
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from users.models import User

from notifications.email_types import validate_recipient

_RELATIVE_URL_ATTR = re.compile(r'\b(href|src)="/(?!/)')
_LINK = re.compile(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
_BLOCK_END = re.compile(r"<br\s*/?>|</(?:p|li|h[1-6]|blockquote)>")


class RenderedBlast(NamedTuple):
    html: str
    text: str


def collect_recipients() -> tuple[list[str], int]:
    emails: list[str] = []
    skipped = 0
    for email in User.objects.members().order_by("created_at").values_list("email", flat=True):
        if not email:
            skipped += 1
            continue
        try:
            validate_recipient(email)
        except ValueError:
            skipped += 1
            continue
        emails.append(email)
    return emails, skipped


def clean_body(body_html: str) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return _RELATIVE_URL_ATTR.sub(rf'\1="{base}/', sanitize_content_html(body_html))


def render_blast(subject: str, body_html: str) -> RenderedBlast:
    body_html = clean_body(body_html)
    with_urls = _BLOCK_END.sub("\n", _LINK.sub(lambda m: f"{m.group(2)} ({m.group(1)})", body_html))
    body_text = html_lib.unescape(strip_tags(with_urls)).strip()
    context = {"subject": subject, "body_html": body_html, "body_text": body_text}
    return RenderedBlast(
        html=render_to_string("emails/member_blast.html", context),
        text=render_to_string("emails/member_blast.txt", context),
    )
