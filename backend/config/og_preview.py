from community.models import Event, EventStatus, PageVisibility, parse_event_ref
from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from config.media_proxy import media_path

# OG descriptions are truncated by most scrapers around 200 chars; trimming
# here keeps the tag tidy and avoids dumping a 2000-char body into <head>.
_OG_DESCRIPTION_MAX = 200

# Anonymous scrapers may only preview what an anonymous user could open in the
# app: public events that aren't drafts or deleted. Cancelled public events are
# still viewable (and shareable), so they get a preview too.
_PREVIEWABLE_STATUSES = frozenset({EventStatus.ACTIVE, EventStatus.CANCELLED})

# Served by nginx from frontend/public — Django static() would need a build-time manifest.
_LOGO_PATH = "/og/pda-logo.png"

# Keep in sync with the static-page location regex in nginx.conf.template.
_STATIC_PAGES = {
    "": ("pda", "vegan collective liberation community"),
    "join": ("join pda", "vegan collective liberation community"),
    "calendar": ("calendar · pda", "upcoming pda events"),
    "donate": ("donate · pda", "support pda"),
    "faq": ("faq · pda", "frequently asked questions"),
    "sms-policy": ("sms policy · pda", "how pda uses text messaging"),
    "guidelines": ("community guidelines · pda", "how we show up for each other"),
}


def _absolute(path: str) -> str:
    """Absolute URL under FRONTEND_BASE_URL; pass through existing http(s) URLs."""
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{path}"


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _render_preview(request, *, title: str, description: str, url: str, image: str):
    response = render(
        request,
        "og/event_preview.html",
        {"title": title, "description": description, "url": url, "image": image},
    )
    response["X-Robots-Tag"] = "noindex"
    return response


def _site_preview(request, path: str):
    title, description = _STATIC_PAGES[""]
    return _render_preview(
        request,
        title=title,
        description=description,
        url=_absolute(path),
        image=_absolute(_LOGO_PATH),
    )


def event_og_preview(request, event_id: str):
    """Render OG/Twitter meta tags for a PUBLIC event so link scrapers can unfurl it.

    Anything an anonymous user can't open gets the generic site preview, so
    member-only details never leak and hidden events look identical to missing ones.
    """
    event = Event.objects.filter(parse_event_ref(event_id).as_q()).first()
    is_previewable = (
        event is not None
        and event.visibility == PageVisibility.PUBLIC
        and event.status in _PREVIEWABLE_STATUSES
    )
    if not is_previewable:
        return _site_preview(request, f"/events/{event_id}")

    return _render_preview(
        request,
        title=event.title,
        description=_truncate(event.description, _OG_DESCRIPTION_MAX),
        url=_absolute(f"/events/{event.slug or event.id}"),
        image=_absolute(media_path(event.photo)),
    )


def static_page_og_preview(request, page: str):
    try:
        title, description = _STATIC_PAGES[page]
    except KeyError:
        raise Http404

    return _render_preview(
        request,
        title=title,
        description=description,
        url=_absolute(f"/{page}"),
        image=_absolute(_LOGO_PATH),
    )
