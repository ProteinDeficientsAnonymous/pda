import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.conf import settings
from django.db.models import Exists, OuterRef
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
from community.models import Event, JoinRequest, JoinRequestStatus, RSVPStatus


def _tentative_q() -> Exists:
    return Exists(
        JoinRequest.objects.filter(user=OuterRef("pk"), status=JoinRequestStatus.TENTATIVE)
    )


def _gets_member_emails(user: User) -> bool:
    """Members and tentative members get member emails; public rsvpers get manage links."""
    return user.is_member or User.objects.filter(pk=user.pk).filter(_tentative_q()).exists()


def _member_email_details(event: Event, user: User) -> MemberRsvpEmailDetails:
    return MemberRsvpEmailDetails(
        to=user.email or "",
        display_name=user.first_name,
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
    """Email a member "you're in" when they become attending. Best-effort; never raises."""
    if status != RSVPStatus.ATTENDING or not user.email:
        return
    _send_member_email(request, event, user, "attending")


def email_host_set_rsvp_status(
    request, event: Event, user: User, previous_status: str | None, status: str
) -> None:
    """Email a signed-in user whose RSVP a host changed. Public rsvpers aren't emailed."""
    if status != previous_status and _gets_member_emails(user):
        email_member_rsvp_status(request, event, user, status)


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
    """Email everyone promoted off the waitlist. Best-effort per user."""
    if not promoted_user_ids:
        return
    promoted = (
        User.objects.filter(id__in=promoted_user_ids)
        .exclude(email__isnull=True)
        .annotate(is_tentative=_tentative_q())
    )
    unpaid = _unpaid_user_ids(event, promoted_user_ids)
    for user in promoted:
        if not user.email:
            continue
        payment_pending = str(user.id) in unpaid
        if user.is_member or user.is_tentative:
            _send_member_email(request, event, user, "promoted", payment_pending)
        else:
            _email_promoted_non_member(request, event, user, payment_pending)
