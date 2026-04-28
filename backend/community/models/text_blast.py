"""Event text blast models — host-triggered SMS to event attendees.

Three records:
- EventTextBlast: one row per blast (the message + filter snapshot).
- EventTextBlastDelivery: one row per recipient per blast (Twilio MessageSid + status).
- EventBlastMute: one row per (event, user) when an invitee replies "M".

Sender + recipient FKs use SET_NULL so a blast survives user deletion as a
record of "what we sent, to which phone" — phone_number is frozen on the
delivery row at send time so inbound webhook lookups still work after a
user changes their number.
"""

import uuid
from typing import TYPE_CHECKING

from django.db import models

from community.models.choices import EventTextBlastDeliveryStatus


class EventTextBlast(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        sender_id: uuid.UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "community.Event",
        on_delete=models.CASCADE,
        related_name="text_blasts",
    )
    sender = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_text_blasts",
    )
    # Body the host typed — pre-suffix. The mute-instruction is composed at
    # send time and not stored here, so we can iterate on the suffix copy
    # without touching old records.
    message = models.TextField(max_length=1000)
    # Snapshot of the recipient filters at send time, e.g.
    # ["attending", "maybe", "invited_no_response"]. Stored as raw strings
    # against RSVPStatus values + RecipientFilterSentinel.INVITED_NO_RESPONSE.
    recipient_filters = models.JSONField(default=list)
    recipient_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"blast on {self.event.title} by {self.sender}"


class EventTextBlastDelivery(models.Model):
    if TYPE_CHECKING:
        blast_id: uuid.UUID
        recipient_id: uuid.UUID | None

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blast = models.ForeignKey(
        EventTextBlast,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    recipient = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="received_text_blasts",
    )
    # Frozen at send time (E.164). The inbound webhook matches incoming
    # "From" against this column to find which event a "M" reply belongs to,
    # so we don't lose the link if the user later changes their number.
    phone_number = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        choices=EventTextBlastDeliveryStatus.choices,
        default=EventTextBlastDeliveryStatus.QUEUED,
    )
    twilio_message_sid = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        indexes = [
            # Inbound webhook does ORDER BY created_at DESC LIMIT 1 to find
            # the most recent blast a phone received.
            models.Index(fields=["phone_number", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.phone_number} ({self.status})"


class EventBlastMute(models.Model):
    if TYPE_CHECKING:
        event_id: uuid.UUID
        user_id: uuid.UUID

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "community.Event",
        on_delete=models.CASCADE,
        related_name="blast_mutes",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="event_blast_mutes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=("event", "user"), name="unique_event_blast_mute"),
        ]

    def __str__(self):
        return f"{self.user} muted {self.event.title}"
