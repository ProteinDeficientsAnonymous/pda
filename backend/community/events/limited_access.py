from django.db.models import Q
from users.models import LIMITED_STATUSES, MembershipStatus

from community.events._hosts import is_draft_host
from community.models import EventType, PageVisibility
from community.validation import Code, raise_validation

# Event types a limited user (signed in, not an active member) engages
# with fully. They're also the two types whose check-in promotes them to member
# (see maybe_promote_tentative), so this is the path into the community.
LIMITED_ACCESS_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)


def is_limited(user) -> bool:
    """Signed in without full access: tentative or attendance-paused; no other status signs in."""
    return user is not None and user.membership_status != MembershipStatus.ACTIVE_MEMBER


# Guidelines-paused, archived and `none` users can't sign in, so they can't be a guest.
_GUEST_STATUSES = (MembershipStatus.ACTIVE_MEMBER, *LIMITED_STATUSES)


def _limited_out_of(user, event) -> bool:
    """A limited user on an event they may only see as a visitor."""
    return is_limited(user) and event.event_type not in LIMITED_ACCESS_EVENT_TYPES


def can_be_guest(user, event) -> bool:
    """Whether a host may add or invite this user to the event."""
    return user.membership_status in _GUEST_STATUSES and not _limited_out_of(user, event)


def limited_access_event_q() -> Q:
    """Rows a limited user may list: anything public, plus official/club."""
    return Q(visibility=PageVisibility.PUBLIC) | Q(event_type__in=LIMITED_ACCESS_EVENT_TYPES)


def event_viewer_for(viewer, event):
    """The viewer to gate one event's fields with.

    Outside official/club, a limited user sees exactly what a logged-out visitor
    sees — so they're downgraded to anonymous rather than filtered out, and a
    public community event stays as visible as it was before they signed in.
    The exception is a draft they host, or created and their pause left hostless.
    """
    if _limited_out_of(viewer, event):
        return viewer if event.is_draft and is_draft_host(event, viewer) else None
    return viewer


def enforce_limited_write_access(user, event, action: str) -> None:
    """Block a limited user from acting on an event they may only read as a visitor."""
    if _limited_out_of(user, event):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action=action)
