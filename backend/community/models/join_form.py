"""JoinFormQuestion and JoinRequest models."""

import uuid

from django.conf import settings
from django.db import models

from community.models._join_request_transitions import (
    normalize_rejection,
    reject_join_request_transition,
    stamp_join_request_status,
    validate_join_request_edge,
)
from community.models.choices import (
    OPEN_JOIN_REQUEST_STATUSES,
    JoinFormQuestionType,
    JoinRequestEvent,
    JoinRequestStatus,
    RejectionReason,
)
from community.validation import Code


class JoinFormQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=300)
    field_type = models.CharField(
        max_length=10,
        choices=JoinFormQuestionType.choices,
        default=JoinFormQuestionType.TEXT,
    )
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "community"
        ordering = ["display_order"]

    def __str__(self):
        return self.label


class JoinRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="join_requests",
    )
    custom_answers = models.JSONField(default=dict, blank=True)
    interested_clubs = models.ManyToManyField(
        "community.Club", blank=True, related_name="interested_join_requests"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
    )
    # Last move between statuses; the audit log keeps the history.
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="status_changed_join_requests",
    )
    # Set when a tentative applicant is auto-approved by checking in at this event.
    approved_via_event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    rejection_reason = models.CharField(
        max_length=30, choices=RejectionReason.choices, blank=True, default=""
    )
    # Free text written by the vetter; required when rejection_reason is OTHER.
    rejection_note = models.TextField(max_length=1000, blank=True, default="")
    # Set when the user checks the SMS-consent box on the join form. Required
    # at the API level, but stored as nullable so historical pre-consent rows
    # remain queryable. Used as proof-of-consent for Twilio toll-free
    # verification + ongoing TCPA defensibility. The automated SMS send path is
    # deferred (see #501); consent is kept for manual group-texting and possible
    # future automation.
    sms_consent_at = models.DateTimeField(null=True, blank=True)
    # Set when the user checks the community-guidelines box on the join form.
    # Required at the API level; nullable so historical pre-consent rows remain
    # queryable. Records that the applicant agreed to the guidelines they read.
    guidelines_consent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "community"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["phone_number", "status"], name="joinrequest_phone_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number"],
                condition=models.Q(status__in=OPEN_JOIN_REQUEST_STATUSES),
                name="unique_open_join_request_per_phone",
            ),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @staticmethod
    def normalize_rejection(reason: str, note: str) -> tuple[str, str]:
        return normalize_rejection(reason, note)

    def mark_tentative(self, *, by=None) -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.MARK_TENTATIVE)
        return stamp_join_request_status(self, target, by)

    def approve(self, *, by=None) -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.APPROVE)
        return stamp_join_request_status(self, target, by)

    def promote_on_check_in(self, *, event, by=None) -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.PROMOTE_ON_CHECK_IN)
        if event is None:
            reject_join_request_transition(
                self, JoinRequestEvent.PROMOTE_ON_CHECK_IN, Code.JoinRequest.INVALID_STATUS
            )
        self.approved_via_event = event
        return [*stamp_join_request_status(self, target, by), "approved_via_event"]

    def reject(self, *, by=None, reason: str = "", note: str = "") -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.REJECT)
        self.rejection_reason, self.rejection_note = normalize_rejection(reason, note)
        return [*stamp_join_request_status(self, target, by), "rejection_reason", "rejection_note"]

    def unreject(self, *, by=None) -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.UNREJECT)
        self.rejection_reason = ""
        self.rejection_note = ""
        return [*stamp_join_request_status(self, target, by), "rejection_reason", "rejection_note"]

    def close(self, *, by=None) -> list[str]:
        target = validate_join_request_edge(self, JoinRequestEvent.CLOSE)
        return stamp_join_request_status(self, target, by)

    @classmethod
    def latest_is_rejected(cls, phone_number: str) -> bool:
        """Whether this phone's newest join request was rejected; they must re-apply."""
        latest = cls.objects.filter(phone_number=phone_number).order_by("-submitted_at")
        return latest.values_list("status", flat=True).first() == JoinRequestStatus.REJECTED

    def __str__(self):
        return f"{self.full_name} ({self.phone_number}) — {self.submitted_at:%Y-%m-%d}"
