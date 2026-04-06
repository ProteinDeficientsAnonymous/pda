"""Event and EventRSVP models."""

import uuid
from typing import TYPE_CHECKING

from django.db import models

from community.models.choices import EventType, InvitePermission, PageVisibility, RSVPStatus

if TYPE_CHECKING:
    from django.db.models import Manager

    from community.models.poll import EventPoll
    from community.models.survey import Survey


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    whatsapp_link = models.URLField(blank=True)
    partiful_link = models.URLField(blank=True)
    other_link = models.URLField(blank=True)
    price = models.CharField(max_length=100, blank=True)
    venmo_link = models.URLField(blank=True)
    cashapp_link = models.URLField(blank=True)
    zelle_info = models.CharField(max_length=200, blank=True)
    rsvp_enabled = models.BooleanField(default=False)
    datetime_tbd = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="event_photos/", blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.COMMUNITY,
    )
    visibility = models.CharField(
        max_length=20,
        choices=PageVisibility.choices,
        default=PageVisibility.PUBLIC,
    )
    invite_permission = models.CharField(
        max_length=20,
        choices=InvitePermission.choices,
        default=InvitePermission.ALL_MEMBERS,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        created_by_id: uuid.UUID | None
        rsvps: "Manager[EventRSVP]"
        surveys: "Manager[Survey]"
        poll: "EventPoll"
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_events",
    )
    co_hosts = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="co_hosted_events",
    )
    invited_users = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="invited_events",
    )

    class Meta:
        app_label = "community"
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} — {self.start_datetime:%Y-%m-%d %H:%M}"


class EventRSVP(models.Model):
    if TYPE_CHECKING:
        user_id: uuid.UUID
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=20, choices=RSVPStatus.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_event_rsvp"),
        ]

    def __str__(self):
        return f"{self.user.display_name or self.user.phone_number} → {self.event.title}: {self.status}"
