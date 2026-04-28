"""Event member-invitation endpoint.

Adds users to event.invited_users with set-union semantics — already-invited
users are silently skipped, never removed. Member invitations live on their
own endpoint (not on event create/update) so that the event form has a
narrow, non-destructive contract: editing an event can never clobber the
invitee list, and inviting can never accidentally rewrite event fields.

Co-host invites are a different flow — see _event_cohost_invites.py.
"""

import logging
from uuid import UUID

from config.audit import audit_log
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.service import create_event_invite_notifications
from pydantic import BaseModel, Field
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._event_helpers import _event_out
from community._event_schemas import EventOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, InvitePermission

router = Router()


class InviteIn(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=100)


def _can_invite_to_event(user, event: Event) -> bool:
    """Mirror the frontend canInvite gate.

    Hosts (creator / co-host) can always invite; managers can always invite;
    other authed members can invite when invite_permission == ALL_MEMBERS.
    """
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.created_by_id == user.pk:
        return True
    if event.co_hosts.filter(pk=user.pk).exists():
        return True
    return event.invite_permission == InvitePermission.ALL_MEMBERS


@router.post(
    "/events/{event_id}/invitations/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def invite_to_event(request, event_id: UUID, payload: InviteIn):
    event = get_object_or_404(
        Event.objects.select_related("created_by").prefetch_related(
            "co_hosts", "invited_users", "rsvps__user"
        ),
        id=event_id,
    )

    if event.is_deleted:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)

    if not _can_invite_to_event(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "invite_to_event"},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="invite_to_event")

    # Past events can still be edited (description tweaks, etc.) but it makes
    # no sense to add new invitees to something that's already happened.
    if event.is_past:
        raise_validation(Code.Perm.DENIED, status_code=403, action="invite_to_past_event")

    existing_ids = set(event.invited_users.values_list("pk", flat=True))
    requested_ids = {UUID(uid) for uid in payload.user_ids}
    new_ids = requested_ids - existing_ids

    if new_ids:
        new_users = UserModel.objects.filter(pk__in=new_ids)
        event.invited_users.add(*new_users)
        if not event.is_draft:
            create_event_invite_notifications(event, [str(uid) for uid in new_ids], request.auth)

    audit_log(
        logging.INFO,
        "event_invitations_added",
        request,
        target_type="event",
        target_id=str(event_id),
        details={
            "requested_count": len(requested_ids),
            "newly_invited_count": len(new_ids),
        },
    )
    event.refresh_from_db()
    return Status(200, _event_out(event, request.auth))
