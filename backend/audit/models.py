import uuid

from django.conf import settings
from django.db import models


class AuditTargetType(models.TextChoices):
    DOC_FOLDER = "doc_folder", "Doc folder"
    DOCUMENT = "document", "Document"
    EDITABLE_PAGE = "editable_page", "Editable page"
    EVENT = "event", "Event"
    EVENT_POLL = "event_poll", "Event poll"
    EVENT_TAG = "event_tag", "Event tag"
    FAQ = "faq", "FAQ"
    FEATURE_FLAG = "feature_flag", "Feature flag"
    GUIDELINES = "guidelines", "Guidelines"
    HOMEPAGE = "homepage", "Homepage"
    JOIN_FORM_QUESTION = "join_form_question", "Join form question"
    JOIN_REQUEST = "join_request", "Join request"
    MEMBER_PROMOTION_MESSAGE = "member_promotion_message", "Member promotion message"
    ROLE = "role", "Role"
    SURVEY = "survey", "Survey"
    SURVEY_QUESTION = "survey_question", "Survey question"
    TENTATIVE_APPROVAL_MESSAGE = "tentative_approval_message", "Tentative approval message"
    USER = "user", "User"
    WELCOME_TEMPLATE = "welcome_template", "Welcome template"
    WHATSAPP_LINK = "whatsapp_link", "WhatsApp link"


class AuditLogEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=64, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    # Snapshot: actor goes NULL on hard delete.
    actor_label = models.CharField(max_length=255)
    target_type = models.CharField(
        max_length=32, choices=AuditTargetType, blank=True, db_index=True
    )
    target_id = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    level = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "audit log entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_label} at {self.created_at:%Y-%m-%d %H:%M}"
