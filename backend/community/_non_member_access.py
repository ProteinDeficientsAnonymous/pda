from django.db.models import Q

from community._validation import Code, raise_validation
from community.models import EventType, PageVisibility

# Event types a signed-in non-member (a tentatively-approved applicant) engages
# with fully. They're also the two types whose check-in promotes them to member
# (see _maybe_promote_tentative), so this is the path into the community.
NON_MEMBER_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)


def is_non_member(user) -> bool:
    return user is not None and not user.is_member


def non_member_event_q() -> Q:
    """Rows a signed-in non-member may list: anything public, plus official/club."""
    return Q(visibility=PageVisibility.PUBLIC) | Q(event_type__in=NON_MEMBER_EVENT_TYPES)


def event_viewer_for(viewer, event):
    """The viewer to gate one event's fields with.

    Outside official/club, a non-member sees exactly what a logged-out visitor
    sees — so they're downgraded to anonymous rather than filtered out, and a
    public community event stays as visible as it was before they signed in.
    """
    if is_non_member(viewer) and event.event_type not in NON_MEMBER_EVENT_TYPES:
        return None
    return viewer


def enforce_non_member_write_access(user, event, action: str) -> None:
    """Block a non-member from acting on an event they may only read as a visitor."""
    if is_non_member(user) and event.event_type not in NON_MEMBER_EVENT_TYPES:
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action=action)
