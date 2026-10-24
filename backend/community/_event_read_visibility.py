from community._cohost_invite_helpers import has_pending_cohost_invite
from community._event_helpers import _can_edit_event, _can_see_invite_only
from community._validation import Code, raise_validation
from community.models import Event, PageVisibility


def _can_see_draft(event: Event, auth_user) -> bool:
    """Pending cohost invitees can see the draft they were invited to so they
    can find the accept/decline banner. They aren't accepted co-hosts yet,
    so `_can_edit_event` returns False — without this branch, they'd 404."""
    if not auth_user:
        return False
    return _can_edit_event(auth_user, event) or has_pending_cohost_invite(event, auth_user)


def _enforce_event_read_visibility(event: Event, auth_user) -> None:
    """Raise the right ValidationException if `auth_user` shouldn't see this event."""
    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if event.is_draft and not _can_see_draft(event, auth_user):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="view_draft_event")
    if event.visibility == PageVisibility.MEMBERS_ONLY and auth_user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if event.visibility == PageVisibility.INVITE_ONLY:
        if not _can_see_invite_only_event(auth_user, event):
            raise_validation(
                Code.Event.PERM_DENIED, status_code=403, action="view_invite_only_event"
            )


def _can_see_invite_only_event(user, event: Event) -> bool:
    """Invite-only visibility without hydrating invitees."""
    if user is None:
        return False
    if _can_see_invite_only(
        user, {str(c.id) for c in event.co_hosts.all()}, set(), event.created_by_id
    ):
        return True
    return event.invited_users.filter(pk=user.pk).exists()
