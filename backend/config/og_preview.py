from uuid import UUID

from community.models import Event, EventStatus, PageVisibility
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


def _absolute(path: str) -> str:
    """Turn a root-relative path into an absolute URL under the public app origin."""
    if not path:
        return ""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{path}"


def _truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def event_og_preview(request, event_id: UUID):
    """Render OG/Twitter meta tags for a PUBLIC event so link scrapers can unfurl it.

    Only public, non-draft, non-deleted events are previewed — mirroring what an
    anonymous user may see. Anything else 404s so member-only details never leak.
    """
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise Http404

    is_previewable = (
        event.visibility == PageVisibility.PUBLIC and event.status in _PREVIEWABLE_STATUSES
    )
    if not is_previewable:
        raise Http404

    url = _absolute(f"/events/{event.id}")
    image = _absolute(media_path(event.photo))

    response = render(
        request,
        "og/event_preview.html",
        {
            "title": event.title,
            "description": _truncate(event.description, _OG_DESCRIPTION_MAX),
            "url": url,
            "image": image,
        },
    )
    response["X-Robots-Tag"] = "noindex"
    return response
