import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.conf import settings
from notifications._email_helpers import (
    MemberRsvpEmailDetails,
    send_member_rsvp_status_email,
    send_rsvp_waitlist_promoted_email,
)
from notifications.email_sender import get_email_sender
from users.models import NonMemberRsvpToken, User

from community._public_rsvp_shared import (
    _email_details,
    _event_links,
    _format_event_when,
    _log_email_failure,
    _unpaid_user_ids,
)
from community._shared import logger
from community.models import Event, RSVPStatus

_MEMBER_STATUS_KINDS: dict[str, str] = {
    RSVPStatus.ATTENDING: "attending",
    RSVPStatus.WAITLISTED: "waitlisted",
    RSVPStatus.MAYBE: "maybe",
    RSVPStatus.CANT_GO: "cant_go",
}


def _member_email_details(event: Event, user: User) -> MemberRsvpEmailDetails:
    return MemberRsvpEmailDetails(
        to=user.email or "",
        display_name=user.full_name,
        event_title=event.title,
        event_when=_format_event_when(event),
        event_location=event.location,
        event_links=_event_links(event),
        event_url=f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.id}",
    )


def _send_member_email(request, event: Event, user: User, kind: str, payment_pending=False):
    try:
        result = send_member_rsvp_status_email(
            sender=get_email_sender(),
            details=_member_email_details(event, user),
            kind=kind,
            payment_pending=payment_pending,
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        logger.warning("member rsvp email failed", exc_info=True)
        audit_log(
            logging.WARNING,
            "member_rsvp_email_failed",
            request,
            target=AuditTarget(
                type=AuditTargetType.EVENT,
                id=str(event.id),
                details={"user_id": str(user.pk), "kind": kind, "error": str(exc)},
            ),
        )


def email_member_rsvp_status(request, event: Event, user: User, status: str) -> None:
    """Email a member their new RSVP status. Best-effort; never raises."""
    kind = _MEMBER_STATUS_KINDS.get(status)
    if kind is None or not user.email:
        return
    _send_member_email(request, event, user, kind)


def _email_promoted_non_member(request, event: Event, user: User, payment_pending: bool) -> None:
    try:
        token = NonMemberRsvpToken.issue_or_extend(user)
        result = send_rsvp_waitlist_promoted_email(
            sender=get_email_sender(),
            details=_email_details(event, user, token.token),
            payment_pending=payment_pending,
        )
        if not result.success:
            raise RuntimeError(result.error or "send returned failure")
    except Exception as exc:
        _log_email_failure(request, event, user, exc)


def email_promoted_users(request, event: Event, promoted_user_ids: list[str]) -> None:
    """Email everyone promoted off the waitlist. Best-effort per user.

    Non-members get their manage-rsvp link; members get a link to the event.
    """
    if not promoted_user_ids:
        return
    promoted = User.objects.filter(id__in=promoted_user_ids).exclude(email__isnull=True)
    unpaid = _unpaid_user_ids(event, promoted_user_ids)
    for user in promoted:
        if not user.email:
            continue
        payment_pending = str(user.id) in unpaid
        if user.is_member:
            _send_member_email(request, event, user, "promoted", payment_pending)
        else:
            _email_promoted_non_member(request, event, user, payment_pending)
