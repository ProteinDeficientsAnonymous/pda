from django import template
from django.template.defaultfilters import linebreaks_filter, urlize
from django.utils.safestring import mark_safe

register = template.Library()

_LINK_STYLE = "color: #3c6939;"
_PARAGRAPH_STYLE = "margin: 0 0 16px;"


@register.filter
def email_body(value: str) -> str:
    """Render an admin-editable plain-text email body as styled HTML.

    Mail clients like Outlook drop <style> blocks, so the anchors and
    paragraphs urlize/linebreaks generate get their styling inlined here.
    Both filters escape first, so the only tags these replacements can touch
    are the ones we just generated — a vetter's literal ``<a>`` is already
    entity-escaped by then.
    """
    html = str(linebreaks_filter(urlize(value)))
    html = html.replace("<a ", f'<a style="{_LINK_STYLE}" ')
    html = html.replace("<p>", f'<p style="{_PARAGRAPH_STYLE}">')
    return mark_safe(html)  # noqa: S308
