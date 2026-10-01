from django.db.models import Q

from community._validation import Code, raise_validation
from community.models import EventType, PageVisibility

# Event types a tentative member (signed in, not yet is_member) engages
# with fully. They're also the two types whose check-in promotes them to member
# (see _maybe_promote_tentative), so this is the path into the community.
TENTATIVE_MEMBER_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)


def is_tentative_member(user) -> bool:
    """Signed in but not a member — only tentative applicants can sign in without is_member."""
    return user is not None and not user.is_member


def tentative_member_event_q() -> Q:
    """Rows a tentative member may list: anything public, plus official/club."""
    return Q(visibility=PageVisibility.PUBLIC) | Q(event_type__in=TENTATIVE_MEMBER_EVENT_TYPES)


def event_viewer_for(viewer, event):
    """The viewer to gate one event's fields with.

    Outside official/club, a tentative member sees exactly what a logged-out visitor
    sees — so they're downgraded to anonymous rather than filtered out, and a
    public community event stays as visible as it was before they signed in.
    """
    if is_tentative_member(viewer) and event.event_type not in TENTATIVE_MEMBER_EVENT_TYPES:
        return None
    return viewer


def enforce_tentative_member_write_access(user, event, action: str) -> None:
    """Block a tentative member from acting on an event they may only read as a visitor."""
    if is_tentative_member(user) and event.event_type not in TENTATIVE_MEMBER_EVENT_TYPES:
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action=action)
