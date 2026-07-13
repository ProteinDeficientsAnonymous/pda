"""EventTag model — a curated, admin-managed set of event categories."""

import uuid

from django.db import models
from django.utils.text import slugify


class EventTag(models.Model):
    """A curated tag an event can carry (e.g. "walk", "restaurant meetup").

    The set is curated via Django admin or in-app by users with the
    ``manage_events`` permission. Events reference tags through the
    ``Event.tags`` M2M; assigning tags to an event reuses the existing
    event-edit gate (creators / co-hosts / managers).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
