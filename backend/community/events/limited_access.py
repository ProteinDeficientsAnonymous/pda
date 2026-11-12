from django.db.models import Q
from users.models import MembershipStatus

from community.events._hosts import is_hosted_by
from community.models import EventType, PageVisibility
from community.validation import Code, raise_validation

# Event types a limited user (signed in, not an active member) engages
# with fully. They're also the two types whose check-in promotes them to member
# (see maybe_promote_tentative), so this is the path into the community.
LIMITED_ACCESS_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)


def is_limited(user) -> bool:
    """Signed in without full access: tentative or attendance-paused; no other status signs in."""
    return user is not None and user.membership_status != MembershipStatus.ACTIVE_MEMBER


def limited_access_event_q() -> Q:
    """Rows a limited user may list: anything public, plus official/club."""
    return Q(visibility=PageVisibility.PUBLIC) | Q(event_type__in=LIMITED_ACCESS_EVENT_TYPES)


def event_viewer_for(viewer, event):
    """The viewer to gate one event's fields with.

    Outside official/club, a limited user sees exactly what a logged-out visitor
    sees — so they're downgraded to anonymous rather than filtered out, and a
    public community event stays as visible as it was before they signed in.
    The exception is a draft they created, such as one their pause drafted.
    """
    if is_limited(viewer) and event.event_type not in LIMITED_ACCESS_EVENT_TYPES:
        return viewer if event.is_draft and is_hosted_by(event, viewer) else None
    return viewer


def enforce_limited_write_access(user, event, action: str) -> None:
    """Block a limited user from acting on an event they may only read as a visitor."""
    if is_limited(user) and event.event_type not in LIMITED_ACCESS_EVENT_TYPES:
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action=action)
