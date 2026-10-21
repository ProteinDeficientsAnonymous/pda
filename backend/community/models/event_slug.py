import uuid
from dataclasses import dataclass

from django.db import models
from django.db.models import Q
from django.utils.text import slugify

SLUG_MAX = 80
# Leaves room inside SlugField(max_length=SLUG_MAX) for a "-<n>" dedupe suffix.
SLUG_BASE_MAX = 70

# Frontend routes that sit beside /events/:id — an event slug equal to one would be unreachable.
RESERVED_EVENT_SLUGS = frozenset({"add", "mine", "manage"})


class EventSlugAlias(models.Model):
    """A slug an event used before a host renamed it, kept so already-shared links still resolve."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=SLUG_MAX, unique=True)
    event = models.ForeignKey(
        "community.Event", on_delete=models.CASCADE, related_name="slug_aliases"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"

    def __str__(self) -> str:
        return self.slug


@dataclass(frozen=True)
class EventRef:
    """A parsed {event_id} path segment: exactly one of event_id or slug is set."""

    event_id: uuid.UUID | None
    slug: str | None

    def as_q(self) -> Q:
        if self.event_id is not None:
            return Q(id=self.event_id)
        # Subquery, not a join, so an event with several aliases still matches as one row.
        renamed_from = EventSlugAlias.objects.filter(slug=self.slug).values("event_id")
        return Q(slug=self.slug) | Q(pk__in=renamed_from)


def parse_event_ref(raw: str) -> EventRef:
    """Parse the {event_id} path segment: a slug, or a UUID so pre-slug shared links keep resolving."""
    try:
        return EventRef(event_id=uuid.UUID(raw), slug=None)
    except ValueError:
        return EventRef(event_id=None, slug=raw)


def event_lookup_q(event_ref: str) -> Q:
    """Match an event by slug (current or renamed-from), or by UUID so pre-slug links keep resolving.

    param event_ref(str): the {event_id} path segment — a slug or a UUID
    return(Q): lookup for exactly one of the two identifier forms
    """
    return parse_event_ref(event_ref).as_q()


def build_event_slug(title: str, manager, exclude_pk=None, aliases=None) -> str:
    """Slugify `title`, appending -2, -3, … until unique in `manager`.

    param title(str): event title to slugify
    param manager(Manager): Event manager to check uniqueness against (the historical
        model's in a migration, Event.objects otherwise)
    param exclude_pk(UUID | None): row to ignore when checking, for re-saves
    param aliases(Manager | None): EventSlugAlias manager whose slugs are also taken;
        None in migrations that predate the alias table
    return(str): a slug unique across events
    """
    base = slugify(title)[:SLUG_BASE_MAX] or "event"
    taken = manager.filter(slug__startswith=base)
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    taken = set(taken.values_list("slug", flat=True)) | RESERVED_EVENT_SLUGS
    if aliases is not None:
        taken |= set(aliases.filter(slug__startswith=base).values_list("slug", flat=True))
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"
