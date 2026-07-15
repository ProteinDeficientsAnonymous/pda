from uuid import UUID

from django.http import HttpRequest
from users.models import NonMemberRsvpToken, User

from community._shared import _authenticated_user
from community.models import Event


def resolve_event_viewer(request: HttpRequest, event_id: UUID) -> "User | None":
    """Resolve the effective viewer for one event: real member, or a non-member
    RSVP-token holder on any public-RSVP-eligible event, or None.

    A valid token unlocks every event that already accepts public RSVPs — the
    same events an anonymous visitor could unlock by submitting the form — so a
    returning non-member reuses one token across events (issue #873). The token
    only unlocks fields gated purely on "is there a user object" (see
    _event_out/_build_list_out); it never satisfies member/creator/co-host
    checks, and posting still requires an actual RSVP (see _can_post_comments).
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
    # Re-derive eligibility per request so an event that drops out of public-RSVP
    # eligibility (MEMBERS_ONLY, cancelled, past, …) stops unlocking immediately.
    event = Event.objects.filter(id=event_id).first()
    if event is None or not event.is_public_rsvp_eligible:
        return None
    return user
