import secrets
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

# Keeps the JWT out of the SSE URL: client trades this short-lived single-use
# ticket for a stream connection (EventSource can't send an auth header).
_SSE_TICKET_TTL = timedelta(seconds=60)


class NotificationType(models.TextChoices):
    EVENT_INVITE = "event_invite", "Event Invite"
    EVENT_CANCELLED = "event_cancelled", "Event Cancelled"
    JOIN_REQUEST = "join_request", "Join Request"
    COHOST_ADDED = "cohost_added", "Co-host Added"  # legacy: pre-invite-approval flow
    COHOST_INVITE = "cohost_invite", "Co-host Invite"
    COHOST_INVITE_ACCEPTED = "cohost_invite_accepted", "Co-host Invite Accepted"
    COHOST_INVITE_DECLINED = "cohost_invite_declined", "Co-host Invite Declined"
    COHOST_REMOVED = "cohost_removed", "Co-host Removed"
    MAGIC_LINK_REQUEST = "magic_link_request", "Magic Link Request"
    WAITLIST_PROMOTED = "waitlist_promoted", "Waitlist Promoted"
    EVENT_FLAGGED = "event_flagged", "Event Flagged"
    COMMENT_REPLY = "comment_reply", "Comment Reply"
    EVENT_COMMENT = "event_comment", "Event Comment"
    COMMENT_REACTION = "comment_reaction", "Comment Reaction"
    RSVP_STATUS_CHANGED = "rsvp_status_changed", "RSVP Status Changed"
    RSVP_DECLINED_NOTE = "rsvp_declined_note", "RSVP Declined Note"
    CHECKIN_NUDGE = "checkin_nudge", "Check-in Nudge"
    PAYMENT_REVOKED = "payment_revoked", "Payment Confirmation Revoked"
    POLL_SEATED_UNPAID = "poll_seated_unpaid", "Seated From Poll, Unpaid"
    ACCOUNT_DELETED = "account_deleted", "Account Deleted"
    EVENT_FEEDBACK = "event_feedback", "Event Feedback"
    SURVEY_RESPONSE = "survey_response", "Survey Response"
    EVENT_UNPUBLISHED = "event_unpublished", "Event Unpublished"
    MEMBER_RESTORED = "member_restored", "Member Restored"
    CHECK_IN_PROMOTION_FAILED = "check_in_promotion_failed", "Check-in Promotion Failed"
    PLANNING_PROPOSED = "planning_proposed", "Planning Proposed"
    PLANNING_WITHDRAWN = "planning_withdrawn", "Planning Withdrawn"
    PLANNING_COMMITTED = "planning_committed", "Planning Committed"
    PLANNING_DECLINED = "planning_declined", "Planning Declined"
    PLANNING_UPCOMING = "planning_upcoming", "Planning Upcoming"
    PLANNING_AVAILABILITY = "planning_availability", "Planning Availability"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.EVENT_INVITE,
    )
    event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    survey = models.ForeignKey(
        "community.Survey",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    related_user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="related_notifications",
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} for {self.recipient}"


class SseTicket(models.Model):
    """Short-lived, single-use ticket authorizing one SSE stream connection."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Opaque high-entropy secret passed as ?ticket=. Indexed for fast lookup.
    token = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sse_tickets",
    )
    # Set only on anonymous tickets: the one public event whose pings they receive.
    event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["expires_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=True) ^ models.Q(event__isnull=True),
                name="sseticket_user_xor_event",
            )
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @classmethod
    def mint_for_user(cls, user) -> "SseTicket":
        return cls.objects.create(
            token=secrets.token_urlsafe(32),
            user=user,
            expires_at=timezone.now() + _SSE_TICKET_TTL,
        )

    @classmethod
    def mint_for_event(cls, event) -> "SseTicket":
        return cls.objects.create(
            token=secrets.token_urlsafe(32),
            event=event,
            expires_at=timezone.now() + _SSE_TICKET_TTL,
        )


class MemberEmailBlastStatus(models.TextChoices):
    SENDING = "sending", "Sending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    UNKNOWN = "unknown", "Unknown"


class MemberEmailBlast(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        "users.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="member_email_blasts",
    )
    subject = models.CharField(max_length=150)
    body_html = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=MemberEmailBlastStatus.choices,
        default=MemberEmailBlastStatus.SENDING,
    )
    recipient_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]
