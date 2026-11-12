from users.permissions import PermissionKey

from community.cohosts.invite_helpers import has_pending_cohost_invite
from community.events._hosts import is_hosted_by
from community.events.helpers import can_see_invite_only
from community.models import Event, PageVisibility
from community.validation import Code, raise_validation


def _can_see_draft(event: Event, auth_user) -> bool:
    """Hosts and creators (as the drafts list shows them), managers, and pending cohost invitees."""
    if not auth_user:
        return False
    return (
        is_hosted_by(event, auth_user)
        or auth_user.has_permission(PermissionKey.MANAGE_EVENTS)
        or has_pending_cohost_invite(event, auth_user)
    )


def enforce_event_read_visibility(event: Event, auth_user) -> None:
    """Raise the right ValidationException if `auth_user` shouldn't see this event."""
    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if event.is_draft and not _can_see_draft(event, auth_user):
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="view_draft_event")
    if event.visibility != PageVisibility.PUBLIC and auth_user is None:
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
    if can_see_invite_only(
        user, {str(c.id) for c in event.co_hosts.all()}, set(), event.created_by_id
    ):
        return True
    return event.invited_users.filter(pk=user.pk).exists()
