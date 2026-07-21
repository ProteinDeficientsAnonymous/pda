from notifications._email_helpers import send_rsvp_removed_email
from notifications.email_sender import get_email_sender
from users.models import NonMemberRsvpToken, User

from community._public_rsvp_shared import _email_details, _log_email_failure
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, RSVPStatus


def ineligible_non_member_rsvps(event: Event):
    """Non-member RSVPs (any status) on `event` not already REMOVED."""
    return EventRSVP.objects.filter(event=event, user__is_member=False).exclude(
        status=RSVPStatus.REMOVED
    )


def guard_or_remove_ineligible_non_members(event: Event, force: bool) -> list[str]:
    """Remove non-member RSVPs when forced, else raise 409 with the count."""
    rsvps = list(ineligible_non_member_rsvps(event))
    if not rsvps:
        return []
    if not force:
        raise_validation(Code.Event.WOULD_REMOVE_NON_MEMBERS, status_code=409, count=len(rsvps))
    user_ids = [str(r.user_id) for r in rsvps]
    EventRSVP.objects.filter(id__in=[r.id for r in rsvps]).update(status=RSVPStatus.REMOVED)
    return user_ids


def email_removed_non_members(request, event: Event, removed_user_ids: list[str]) -> None:
    """Email any removed non-members. Best-effort per user, mirrors _email_promoted_non_members."""
    if not removed_user_ids:
        return
    removed = User.objects.filter(id__in=removed_user_ids, is_member=False, email__isnull=False)
    for user in removed:
        if not user.email:
            continue
        try:
            token = NonMemberRsvpToken.issue_or_extend(user)
            result = send_rsvp_removed_email(
                sender=get_email_sender(),
                details=_email_details(event, user, token.token),
            )
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            _log_email_failure(request, event, user, exc)
