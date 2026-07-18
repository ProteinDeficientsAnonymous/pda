import logging

from config.audit import audit_log
from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import EventInviteEmailDetails, send_event_invite_email
from notifications.email_sender import get_email_sender
from users._helpers import visible_display_name
from users.models import User as UserModel

from community._shared import logger
from community.models import Event


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return ""
    local = timezone.localtime(event.start_datetime)
    return local.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")


def email_invited_members(request, event: Event, new_user_ids: list[str], inviter) -> None:
    """Best-effort email to each newly invited member with an address on file.

    Legacy accounts may have no email on file — those are skipped rather than raising.
    """
    recipients = (
        UserModel.objects.filter(pk__in=new_user_ids).exclude(email__isnull=True).exclude(email="")
    )
    if not recipients:
        return

    sender = get_email_sender()
    inviter_name = visible_display_name(inviter, None)
    event_when = _format_event_when(event)
    event_url = f"{settings.FRONTEND_BASE_URL}/events/{event.id}"

    for user in recipients:
        try:
            details = EventInviteEmailDetails(
                to=user.email,
                display_name=user.full_name,
                inviter_name=inviter_name,
                event_title=event.title,
                event_when=event_when,
                event_url=event_url,
            )
            result = send_event_invite_email(sender=sender, details=details)
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            logger.warning("event invite email failed", exc_info=True)
            audit_log(
                logging.WARNING,
                "event_invite_email_failed",
                request,
                target_type="event",
                target_id=str(event.id),
                details={"user_id": str(user.pk), "error": str(exc)},
            )
