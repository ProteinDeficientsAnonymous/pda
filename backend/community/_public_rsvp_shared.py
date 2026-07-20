import logging

from config.audit import audit_log
from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import (
    RsvpEmailDetails,
    send_rsvp_waitlist_promoted_email,
)
from notifications.email_sender import get_email_sender
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_schemas import EventOut
from community._shared import logger
from community._validation import Code, raise_validation
from community.models import Event


class PublicRsvpStateOut(BaseModel):
    status: str
    has_plus_one: bool


class PublicRsvpOut(BaseModel):
    event: EventOut
    rsvp: PublicRsvpStateOut
    rsvp_token: str


def _load_public_rsvp_event(event_id) -> Event:
    """Fetch a public-RSVP event: 404 if it can't be seen at all, else 400 with the
    specific reason if it's visible but closed — mirrors _validate_rsvp_access."""
    event = Event.objects.prefetch_related("co_hosts", "invited_users").filter(id=event_id).first()
    if event is None or not event.is_public_rsvp_visible:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not event.rsvp_enabled:
        raise_validation(Code.Event.RSVPS_NOT_ENABLED, status_code=400)
    if event.is_cancelled:
        raise_validation(Code.Event.RSVPS_CLOSED_CANCELLED, status_code=400)
    if event.is_past:
        raise_validation(Code.Event.RSVPS_CLOSED_PAST, status_code=400)
    return event


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
        display_name=user.full_name,
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


def _email_promoted_non_members(request, event: Event, promoted_user_ids: list[str]) -> None:
    """Email any promoted non-members their manage link. Best-effort per user."""
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
