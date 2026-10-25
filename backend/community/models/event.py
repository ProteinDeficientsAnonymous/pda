import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Max, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from community.models.choices import (
    RSVP_QUESTION_TYPE_CHOICES,
    AttendanceStatus,
    EventFlagStatus,
    EventStatus,
    EventType,
    InvitePermission,
    PageVisibility,
    RSVPStatus,
)
from community.models.event_slug import EventSlugAlias, build_event_slug

if TYPE_CHECKING:
    from django.db.models import Manager

    from community.models.cohost_invite import EventCoHostInvite
    from community.models.comment import EventComment
    from community.models.poll import EventPoll
    from community.models.survey import Survey


# How long an event with no end_datetime is treated as running; mirrors frontend DEFAULT_EVENT_DURATION_MS.
DEFAULT_EVENT_DURATION = timedelta(hours=2)


def _is_past_q(now, prefix: str = "") -> Q:
    """Queryset mirror of Event.is_past, over the field path at `prefix` (e.g. "event__")."""
    end = f"{prefix}end_datetime"
    start = f"{prefix}start_datetime"
    return Q(**{f"{prefix}datetime_tbd": False}) & (
        Q(**{f"{end}__lt": now})
        | Q(**{f"{end}__isnull": True, f"{start}__lt": now - DEFAULT_EVENT_DURATION})
    )


def public_rsvp_eligible_q(now, prefix: str = "") -> Q:
    """The single public-RSVP eligibility gate as a Q, over the field path at `prefix`.

    Object-level (Event.is_public_rsvp_eligible) and queryset-level callers share this,
    so the gate can never drift between the write path and the read path.
    """
    return (
        Q(**{f"{prefix}event_type": EventType.OFFICIAL})
        & Q(**{f"{prefix}status": EventStatus.ACTIVE})
        & Q(**{f"{prefix}visibility": PageVisibility.PUBLIC})
        & Q(**{f"{prefix}rsvp_enabled": True})
        & ~_is_past_q(now, prefix)
    )


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    description = models.TextField(blank=True, max_length=3000)
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
    is_partiful_import = models.BooleanField(default=False)
    is_legacy = models.BooleanField(default=False)
    datetime_tbd = models.BooleanField(default=False)
    allow_plus_ones = models.BooleanField(default=False)
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    photo = models.ImageField(upload_to="event_photos/", blank=True)
    photo_updated_at = models.DateTimeField(null=True, blank=True)
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
    checkin_nudge_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        created_by_id: uuid.UUID | None
        rsvps: "Manager[EventRSVP]"
        surveys: "Manager[Survey]"
        poll: "EventPoll"
        comments: "Manager[EventComment]"
        cohost_invites: "Manager[EventCoHostInvite]"
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
    tags = models.ManyToManyField(
        "community.EventTag",
        blank=True,
        related_name="events",
    )

    class Meta:
        app_label = "community"
        ordering = ["start_datetime"]

    def save(self, *args, **kwargs):
        # Assigned once and never regenerated on title edits, so shared links never break.
        if not self.slug:
            self.slug = build_event_slug(
                self.title, Event.objects, exclude_pk=self.pk, aliases=EventSlugAlias.objects
            )
            if (update_fields := kwargs.get("update_fields")) is not None:
                kwargs["update_fields"] = {*update_fields, "slug"}
        super().save(*args, **kwargs)

    @property
    def is_public_rsvp_visible(self) -> bool:
        """Event exists in a state a public visitor may even know about (Issue 973).

        Split out of is_public_rsvp_eligible so callers can 404 on "can't see this
        event" while still 400-ing with a specific reason when it's visible but closed
        (cancelled / past / rsvp-disabled) — matching the member-side RSVP error codes.
        """
        return (
            self.event_type == EventType.OFFICIAL
            and self.visibility == PageVisibility.PUBLIC
            and self.status not in (EventStatus.DRAFT, EventStatus.DELETED)
        )

    @property
    def is_public_rsvp_eligible(self) -> bool:
        """Object-level mirror of public_rsvp_eligible_q()."""
        return (
            self.is_public_rsvp_visible
            and self.status == EventStatus.ACTIVE
            and self.rsvp_enabled
            and not self.is_past
        )

    @property
    def is_past(self) -> bool:
        # TBD events have no decided time, so they're explicitly not "past" —
        # RSVPs, cohost invites, cancellations, etc. should all still apply.
        # Treating them as past silently broke the RSVP section, the
        # standalone-invited card, the cohost-invite banner, and admin filters.
        if self.datetime_tbd:
            return False
        if self.end_datetime is not None:
            return self.end_datetime < timezone.now()
        if self.start_datetime is None:
            return False
        return self.start_datetime + DEFAULT_EVENT_DURATION < timezone.now()

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


@receiver(post_save, sender=Event)
def seed_creator_as_host(sender, instance, created, **kwargs):
    """co_hosts is the sole source of truth for hosts; seed the creator so
    they can step down later. created_by is a separate, permanent audit field."""
    if created and instance.created_by_id is not None:
        instance.co_hosts.add(instance.created_by_id)


class EventRSVP(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        user_id: uuid.UUID
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=20, choices=RSVPStatus.choices)
    has_plus_one = models.BooleanField(default=False)
    questionnaire_responses = models.JSONField(default=dict, blank=True)
    attendance = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.UNKNOWN,
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    plus_one_attendance = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.UNKNOWN,
    )
    plus_one_checked_in_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    pre_cancel_status = models.CharField(
        max_length=20, choices=RSVPStatus.choices, null=True, blank=True
    )
    # Guest's own "i paid" attestation; gates attending writes. Host verification is separate.
    paid_confirmed_at = models.DateTimeField(null=True, blank=True)
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    payment_verified_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_verified_rsvps",
    )
    # Set on joining the waitlist, cleared on leaving; hosts can renumber via the reorder endpoint.
    waitlist_position = models.PositiveIntegerField(null=True, blank=True)
    # Stamped on create and on any status change (see save()); bulk .update() callers must set it.
    status_changed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status as last loaded/saved; None when status was deferred.
    _loaded_status: str | None = None

    class Meta:
        app_label = "community"
        ordering = ["created_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_event_rsvp"),
        ]

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if "status" in field_names:
            instance._loaded_status = instance.status
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        if fields is None or "status" in fields:
            self._loaded_status = self.__dict__.get("status")

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        extra_fields: set[str] = set()

        position = self._resolved_waitlist_position()
        if position != self.waitlist_position:
            self.waitlist_position = position
            extra_fields.add("waitlist_position")

        persists_status = update_fields is None or "status" in update_fields
        if persists_status and self._status_is_new(update_fields):
            self.status_changed_at = timezone.now()
            extra_fields.add("status_changed_at")

        if update_fields is not None and extra_fields:
            kwargs["update_fields"] = {*update_fields, *extra_fields}
        super().save(*args, **kwargs)
        if persists_status:
            self._loaded_status = self.status

    def _status_is_new(self, update_fields) -> bool:
        if self._state.adding:
            return True
        if self._loaded_status is None:
            return update_fields is not None or "status" in self.__dict__
        return self._loaded_status != self.status

    def _resolved_waitlist_position(self) -> int | None:
        # Callers hold the event row lock, so max+1 can't race with another joiner.
        if self.status != RSVPStatus.WAITLISTED:
            return None
        if self.waitlist_position is not None:
            return self.waitlist_position
        last = (
            EventRSVP.objects.filter(event_id=self.event_id, status=RSVPStatus.WAITLISTED)
            .exclude(pk=self.pk)
            .aggregate(m=Max("waitlist_position"))["m"]
        )
        return (last or 0) + 1

    def __str__(self):
        return (
            f"{self.user.full_name or self.user.phone_number} → {self.event.title}: {self.status}"
        )


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


class EventEmailBlast(models.Model):
    """A record of an email blast a host sent to an event's attendees."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="email_blasts")
    sender = models.ForeignKey(
        "users.User", null=True, on_delete=models.SET_NULL, related_name="event_email_blasts"
    )
    subject = models.CharField(max_length=150)
    body = models.TextField(max_length=5000)
    audience = models.CharField(max_length=120, blank=True)
    # successful sends only; attempts = recipient_count + failed_count
    recipient_count = models.PositiveIntegerField(default=0)
    skipped_no_email_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Blast '{self.subject}' to '{self.event.title}'"


class EventRsvpQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvp_questions")
    label = models.CharField(max_length=300)
    field_type = models.CharField(max_length=20, choices=RSVP_QUESTION_TYPE_CHOICES)
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "community"
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.label} ({self.event.title})"
