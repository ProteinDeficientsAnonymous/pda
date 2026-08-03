"""Audit logging helper for structured security and admin action logging."""

import logging

from django.db import models

from config.ratelimit import client_ip

_audit_logger = logging.getLogger("pda.audit")


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


def audit_log(  # noqa: PLR0913
    level: int,
    action: str,
    request,
    target_type: AuditTargetType | str = "",
    target_id: str = "",
    details: dict | None = None,
) -> None:
    """Emit a structured audit log entry.

    Args:
        level: logging.INFO or logging.WARNING
        action: verb describing the event (e.g. 'login_success', 'user_deleted')
        request: the Django/Ninja HttpRequest (used for actor and IP)
        target_type: AuditTargetType member for the affected object
        target_id: string ID of the affected object
        details: optional context dict (avoid including raw phone numbers or tokens)
    """
    user = getattr(request, "auth", None)
    if user and hasattr(user, "pk"):
        actor_id = str(user.pk)
        actor_name = getattr(user, "full_name", None) or str(user)
    else:
        actor_id = "anonymous"
        actor_name = "anonymous"

    # Spoof-resistant client IP (rightmost-untrusted hop); see config/ratelimit.py.
    ip_address = client_ip(request)

    _audit_logger.log(
        level,
        "%s by %s",
        action,
        actor_name,
        extra={
            "audit": True,
            "action": action,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
            "ip_address": ip_address,
        },
    )
