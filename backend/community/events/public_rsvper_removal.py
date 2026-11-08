from django.utils import timezone
from notifications.email_helpers import send_rsvp_removed_email
from notifications.email_sender import get_email_sender
from users.models import PublicRsvpToken, User

from community.events.limited_access import LIMITED_ACCESS_EVENT_TYPES
from community.models import Event, EventRSVP, RSVPStatus
from community.rsvps.public_shared import email_details, log_email_failure
from community.validation import Code, raise_validation


def ineligible_public_rsvper_rsvps(event: Event):
    """Non-member RSVPs (any status) on `event` not already REMOVED."""
    rsvps = EventRSVP.objects.filter(event=event, user__is_member=False).exclude(
        status=RSVPStatus.REMOVED
    )
    if event.event_type in LIMITED_ACCESS_EVENT_TYPES:
        # Limited users keep official/club access regardless of public RSVP eligibility.
        rsvps = rsvps.exclude(user__in=User.objects.limited_users())
    return rsvps


def guard_or_remove_ineligible_public_rsvpers(event: Event, force: bool) -> list[str]:
    """Remove non-member RSVPs when forced, else raise 409 with the count."""
    rsvps = list(ineligible_public_rsvper_rsvps(event))
    if not rsvps:
        return []
    if not force:
        raise_validation(Code.Event.WOULD_REMOVE_NON_MEMBERS, status_code=409, count=len(rsvps))
    user_ids = [str(r.user_id) for r in rsvps]
    EventRSVP.objects.filter(id__in=[r.id for r in rsvps]).update(
        status=RSVPStatus.REMOVED, status_changed_at=timezone.now()
    )
    return user_ids


def email_removed_public_rsvpers(request, event: Event, removed_user_ids: list[str]) -> None:
    """Email any removed public rsvpers. Best-effort per user, mirrors email_promoted_users."""
    if not removed_user_ids:
        return
    # This email and its join pitch are for people without an account.
    removed = User.objects.filter(
        id__in=removed_user_ids, is_member=False, email__isnull=False
    ).exclude(pk__in=User.objects.limited_users())
    for user in removed:
        if not user.email:
            continue
        try:
            token = PublicRsvpToken.issue_or_extend(user)
            result = send_rsvp_removed_email(
                sender=get_email_sender(),
                details=email_details(event, user, token.token),
            )
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            log_email_failure(request, event, user, exc)
