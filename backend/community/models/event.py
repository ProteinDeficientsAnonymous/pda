"""Event and EventRSVP models."""

import uuid
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from community.models.choices import (
    AttendanceStatus,
    EventFlagStatus,
    EventStatus,
    EventType,
    InvitePermission,
    PageVisibility,
    RSVPStatus,
)

if TYPE_CHECKING:
    from django.db.models import Manager

    from community.models.poll import EventPoll
    from community.models.survey import Survey


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, max_length=2000)
    start_datetime = models.DateTimeField(null=True, blank=True)
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
    allow_plus_ones = models.BooleanField(default=False)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
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
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.ACTIVE,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
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

    @property
    def is_past(self) -> bool:
        cutoff = self.end_datetime or self.start_datetime
        if cutoff is None:
            return True
        return cutoff < timezone.now()

    @property
    def is_draft(self) -> bool:
        return self.status == EventStatus.DRAFT

    @property
    def is_cancelled(self) -> bool:
        return self.status == EventStatus.CANCELLED

    @property
    def is_deleted(self) -> bool:
        return self.status == EventStatus.DELETED

    def __str__(self):
        dt = self.start_datetime
        return f"{self.title} — {dt:%Y-%m-%d %H:%M}" if dt else f"{self.title} — TBD"


class EventRSVP(models.Model):
    if TYPE_CHECKING:
        user_id: uuid.UUID
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=20, choices=RSVPStatus.choices)
    has_plus_one = models.BooleanField(default=False)
    attendance = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.UNKNOWN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_event_rsvp"),
        ]

    def __str__(self):
        return f"{self.user.display_name or self.user.phone_number} → {self.event.title}: {self.status}"


class EventFlag(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="flags")
    flagged_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="event_flags",
    )
    reason = models.TextField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=EventFlagStatus.choices,
        default=EventFlagStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "flagged_by"], name="unique_event_flag"),
        ]

    def __str__(self):
        return f"Flag on '{self.event.title}' by {self.flagged_by}"
