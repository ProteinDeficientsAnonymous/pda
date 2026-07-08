"""Event tags endpoint — lists the curated, admin-managed tag set.

The tag set itself is managed via Django admin; this endpoint is read-only and
public so the calendar and event UI can render and filter by tag.
"""

from ninja import Router
from ninja.responses import Status

from community._event_schemas import TagOut
from community.models import EventTag

router = Router()


@router.get("/event-tags/", response={200: list[TagOut]}, auth=None)
def list_event_tags(request):
    return Status(
        200,
        [TagOut(id=str(t.id), name=t.name, slug=t.slug) for t in EventTag.objects.all()],
    )
