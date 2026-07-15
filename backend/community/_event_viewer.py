from uuid import UUID

from django.http import HttpRequest
from users.models import NonMemberRsvpToken, User

from community._shared import _authenticated_user
from community.models import Event, EventRSVP


def resolve_event_viewer(request: HttpRequest, event_id: UUID) -> "User | None":
    """Resolve the effective viewer for one event: real member, or a non-member
    RSVP-token holder scoped to this event, or None.

    A token only unlocks fields already gated purely on "is there a user
    object" (see _event_out/_build_list_out) — it must never satisfy
    permission checks that require real member/creator/co-host identity.
    """
    auth_user = _authenticated_user(getattr(request, "auth", None))
    if auth_user is not None:
        return auth_user

    token = request.GET.get("token", "")
    if not token:
        return None
    user = NonMemberRsvpToken.resolve_user(token)
    if user is None:
        return None
    rsvp = EventRSVP.objects.filter(event_id=event_id, user=user).select_related("event").first()
    if rsvp is None:
        return None
    # Re-derive eligibility on every request — else an event that turns
    # MEMBERS_ONLY (or otherwise drops out) after the RSVP keeps leaking its
    # member-only fields to the token holder (mirrors _eligible_event_rsvps).
    event: Event = rsvp.event
    if not event.is_public_rsvp_eligible:
        return None
    return user
