"""Shared best-effort RSVP email helpers.

Used by both the public RSVP endpoint and the member RSVP endpoints so that a
non-member promoted off the waitlist gets a manage-link email no matter which
path freed the spot. A send failure must never roll back the RSVP.
"""

import logging

from config.audit import audit_log
from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import (
    RsvpEmailDetails,
    send_rsvp_confirmation_email,
    send_rsvp_waitlist_promoted_email,
)
from notifications.email_sender import get_email_sender
from users.models import NonMemberRsvpToken, User

from community._shared import logger
from community.models import Event


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    local = timezone.localtime(event.start_datetime)
    return local.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")


def _event_links(event: Event) -> list[str]:
    return [link for link in (event.whatsapp_link, event.partiful_link, event.other_link) if link]


def _email_details(event: Event, user: User, token_str: str) -> RsvpEmailDetails:
    return RsvpEmailDetails(
        to=user.email,
        display_name=user.display_name,
        event_title=event.title,
        event_when=_format_event_when(event),
        event_location=event.location,
        event_links=_event_links(event),
        manage_url=f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token_str}",
        join_url=f"{settings.FRONTEND_BASE_URL}/join",
    )


def _log_email_failure(request, event: Event, user: User, exc: Exception) -> None:
    logger.warning("public rsvp email failed", exc_info=True)
    audit_log(
        logging.WARNING,
        "public_rsvp_email_failed",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "error": str(exc)},
    )


def send_confirmation_email(
    request, event: Event, user: User, token_str: str, waitlisted: bool
) -> None:
    """Best-effort confirmation email. A send failure must NOT roll back the RSVP."""
    if not user.email:
        return
    try:
        result = send_rsvp_confirmation_email(
            sender=get_email_sender(),
            details=_email_details(event, user, token_str),
            waitlisted=waitlisted,
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        _log_email_failure(request, event, user, exc)


def email_promoted_non_members(request, event: Event, promoted_user_ids: list[str]) -> None:
    """Email any promoted non-members a fresh manage link. Best-effort per user."""
    if not promoted_user_ids:
        return
    promoted = User.objects.filter(id__in=promoted_user_ids, is_member=False, email__isnull=False)
    for user in promoted:
        if not user.email:
            continue
        try:
            token = NonMemberRsvpToken.issue_or_extend(user)
            result = send_rsvp_waitlist_promoted_email(
                sender=get_email_sender(),
                details=_email_details(event, user, token.token),
            )
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            _log_email_failure(request, event, user, exc)
