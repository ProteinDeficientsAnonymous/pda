"""Event member-invitation endpoint.

Adds users to event.invited_users with set-union semantics — already-invited
users are silently skipped, never removed. Member invitations live on their
own endpoint (not on event create/update) so that the event form has a
narrow, non-destructive contract: editing an event can never clobber the
invitee list, and inviting can never accidentally rewrite event fields.

Co-host invites are a different flow — see cohosts/invites.py.
"""

import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.responses import Status
from notifications.service import create_event_invite_notifications
from pydantic import BaseModel, Field
from users.models import User as UserModel
from users.permissions import PermissionKey

from community.events._invite_email import email_invited_members
from community.events.helpers import event_out, reload_event_or_404
from community.events.limited_access import can_be_guest
from community.events.schemas import EventOut
from community.models import Event, EventStatus, InvitePermission, RSVPStatus
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()
_RSVPD = (RSVPStatus.ATTENDING, RSVPStatus.MAYBE)


class InviteIn(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=100)


def can_invite_to_event(user, event: Event) -> bool:
    """Same rule as the frontend's invite button (eventMemberSectionFlags)."""
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.co_hosts.filter(pk=user.pk).exists():
        return True
    return (
        event.invite_permission == InvitePermission.ALL_MEMBERS
        and event.rsvps.filter(user=user, status__in=_RSVPD).exists()
    )


def closed_to_invites(event: Event) -> str | None:
    """return(str | None): why nobody can be invited, as a denied action, or None."""
    if event.status == EventStatus.CANCELLED:
        return "invite_to_cancelled_event"
    # Past events can still be edited, but new invitees make no sense.
    if event.is_past:
        return "invite_to_past_event"
    if not event.rsvp_enabled:
        return "invite_without_rsvp"
    return None


def _eligible_invitees(event: Event, user_ids: set[UUID]) -> list[UserModel]:
    """All-or-nothing: one invitee who can't see the event refuses the whole batch."""
    users = list(UserModel.objects.filter(pk__in=user_ids))
    if not all(can_be_guest(user, event) for user in users):
        raise_validation(Code.Event.GUEST_NOT_ELIGIBLE, status_code=400)
    return users


@router.post(
    "/events/{event_id}/invitations/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
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

    if not can_invite_to_event(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.EVENT,
                id=str(event_id),
                details={"endpoint": "invite_to_event"},
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="invite_to_event")

    closed = closed_to_invites(event)
    if closed:
        raise_validation(Code.Perm.DENIED, status_code=403, action=closed)

    existing_ids = set(event.invited_users.values_list("pk", flat=True))
    requested_ids = {UUID(uid) for uid in payload.user_ids}
    new_ids = requested_ids - existing_ids

    if new_ids:
        new_users = _eligible_invitees(event, new_ids)
        event.invited_users.add(*new_users)
        if not event.is_draft:
            new_id_strs = [str(uid) for uid in new_ids]
            create_event_invite_notifications(event, new_id_strs, request.auth)
            email_invited_members(request, event, new_id_strs, request.auth)

    audit_log(
        logging.INFO,
        "event_invitations_added",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event_id),
            details={
                "requested_count": len(requested_ids),
                "newly_invited_count": len(new_ids),
            },
        ),
    )
    return Status(200, event_out(reload_event_or_404(event_id), request.auth))
