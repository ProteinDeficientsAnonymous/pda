"""Status transition helpers for Event lifecycle changes."""

import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.db import transaction
from django.utils import timezone
from ninja.responses import Status
from notifications._cohost_notifications import create_cohost_invite_notifications
from notifications.models import Notification, NotificationType
from notifications.service import (
    broadcast_event_created,
    create_event_cancellation_notifications,
    create_event_invite_notifications,
)
from users.permissions import PermissionKey

from community._cohost_invite_helpers import diff_cohost_invites, send_cohost_invite_emails
from community._event_helpers import _event_out, _has_attendees
from community._rsvp_counts import _host_crew_ids
from community._validation import Code, raise_validation
from community.models import Event, EventRSVP, EventStatus


def _audit_event(request, event: Event, action: str, details: dict | None = None) -> None:
    audit_log(
        logging.INFO,
        action,
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event.id),
            details={"title": event.title, **(details or {})},
        ),
    )


def _cancel_event(request, event: Event, notify: bool) -> None:
    """ACTIVE → CANCELLED. Raises ValidationException on failure."""
    if event.is_past:
        raise_validation(Code.Event.PAST_CANNOT_BE_CANCELLED, status_code=400)
    if not _has_attendees(event):
        raise_validation(Code.Event.NO_ATTENDEES_CANNOT_BE_CANCELLED, status_code=400)
    event.status = EventStatus.CANCELLED
    event.save(update_fields=["status"])
    if notify:
        create_event_cancellation_notifications(event, request.auth)
    _audit_event(request, event, "event_cancelled", {"notify_attendees": notify})


def _delete_event(request, event: Event) -> None:
    """ACTIVE|CANCELLED|DRAFT → DELETED. Raises ValidationException on failure."""
    if event.status == EventStatus.ACTIVE and not event.is_past and _has_attendees(event):
        raise_validation(Code.Event.CANCEL_BEFORE_DELETE, status_code=400)
    event.status = EventStatus.DELETED
    event.deleted_at = timezone.now()
    event.save(update_fields=["status", "deleted_at"])
    _audit_event(request, event, "event_deleted")


def _uncancel_event(request, event: Event) -> None:
    """CANCELLED → ACTIVE. Permission check is the caller's responsibility."""
    event.status = EventStatus.ACTIVE
    event.save(update_fields=["status"])
    transaction.on_commit(lambda: broadcast_event_created(event))
    _audit_event(request, event, "event_uncancelled")


def _set_event_participants(request, event: Event, co_host_ids: list) -> None:
    """Attach co-hosts to the event and send invite notifications.

    Co-hosts go through the invite-approval flow: requested ids become PENDING
    invites that the invitee can accept or decline. Even on drafts, invites are
    created (and notified once step 3 wires the notification helper) — co-hosts
    are collaborators on the draft, not just downstream attendees.

    Member invitations (vs. co-host invitations) are handled by the dedicated
    POST /events/{id}/invitations/ endpoint, not by event create/update.
    """
    if co_host_ids:
        newly_invited, _ = diff_cohost_invites(event, co_host_ids, request.auth)
        if newly_invited:
            create_cohost_invite_notifications(event, newly_invited, request.auth)
            send_cohost_invite_emails(event, newly_invited, request.auth)


def _publish_draft(request, event: Event) -> None:
    """DRAFT → ACTIVE. Re-validates dates, fires invitee notifications, audit logs."""
    if event.start_datetime is None and not event.datetime_tbd:
        raise_validation(
            Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD,
            field="start_datetime",
            status_code=400,
        )
    if not event.datetime_tbd and event.start_datetime and event.start_datetime < timezone.now():
        raise_validation(
            Code.Event.START_DATETIME_MUST_BE_FUTURE, field="start_datetime", status_code=400
        )
    event.status = EventStatus.ACTIVE
    event.save(update_fields=["status"])
    transaction.on_commit(lambda: broadcast_event_created(event))
    _notify_new_invitees(request, event)
    _audit_event(request, event, "event_published")


def _notify_new_invitees(request, event: Event) -> None:
    """Notify invited members who don't already have an invite for this event.

    Unpublish deletes the EVENT_INVITE rows (see `_unpublish_event`), so a
    publish → unpublish → publish cycle re-creates them — each invitee holds
    exactly one invite notification at any time. The filter also skips any
    rows that survived from an earlier publish, so nobody is re-notified.
    """
    invited_ids = [str(u.id) for u in event.invited_users.all()]
    if not invited_ids:
        return
    already_notified = {
        str(uid)
        for uid in Notification.objects.filter(
            event=event,
            notification_type=NotificationType.EVENT_INVITE,
            recipient_id__in=invited_ids,
        ).values_list("recipient_id", flat=True)
    }
    fresh_ids = [uid for uid in invited_ids if uid not in already_notified]
    if fresh_ids:
        create_event_invite_notifications(event, fresh_ids, request.auth)


def _unpublish_event(request, event: Event) -> None:
    """ACTIVE → DRAFT. Allowed only with zero non-host RSVP rows; silent (nobody to notify)."""
    if event.is_past:
        raise_validation(Code.Event.PAST_CANNOT_BE_UNPUBLISHED, status_code=400)
    # Lock the event row first — the RSVP write path locks it before inserting,
    # so the check can't race an in-flight rsvp into a now-draft event.
    locked = Event.objects.select_for_update().get(pk=event.pk)
    # The host crew's own rsvps (creator + co-hosts) don't block; only rsvps
    # from everyone else do. Fresh query, matching the count exposed as
    # `guest_rsvp_count` on EventOut — count 0 ⇔ this guard passes.
    host_ids = _host_crew_ids(locked)
    if EventRSVP.objects.filter(event=locked).exclude(user_id__in=host_ids).exists():
        raise_validation(Code.Event.HAS_RSVPS, status_code=400)
    event.status = EventStatus.DRAFT
    event.save(update_fields=["status"])
    # A draft is invisible to invitees, so its in-app invites go with the
    # publish that made them visible — republish re-creates them via
    # _notify_new_invitees, leaving each invitee exactly one at any time.
    # Email can't be recalled; only the Notification rows are deleted.
    Notification.objects.filter(
        event=event,
        notification_type=NotificationType.EVENT_INVITE,
    ).delete()
    _audit_event(request, event, "event_unpublished")


def _apply_status_transition(request, event: Event, new_status: str, notify: bool) -> None:
    """Validate and apply a status transition. Raises ValidationException on failure."""
    current = event.status
    if current == new_status:
        return
    if current == EventStatus.DRAFT and new_status == EventStatus.ACTIVE:
        _publish_draft(request, event)
        return
    if new_status == EventStatus.DELETED:
        _delete_event(request, event)
        return
    if current == EventStatus.ACTIVE and new_status == EventStatus.CANCELLED:
        _cancel_event(request, event, notify)
        return
    if current == EventStatus.ACTIVE and new_status == EventStatus.DRAFT:
        _unpublish_event(request, event)
        return
    if current == EventStatus.CANCELLED and new_status == EventStatus.ACTIVE:
        _uncancel_event(request, event)
        return
    raise_validation(
        Code.Event.INVALID_STATUS_TRANSITION,
        status_code=400,
        current=current,
        requested=new_status,
    )


def _handle_status_update(request, event: Event, new_status: str, notify: bool):
    """Apply a status transition from update_event.

    Returns a Status response to send immediately (for DELETE, which exits early
    with the event representation), or None to continue processing field edits.
    Raises ValidationException on validation failures.
    """
    if new_status == EventStatus.ACTIVE and event.is_cancelled:
        is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
        is_host = event.co_hosts.filter(pk=request.auth.pk).exists()
        if not is_host and not is_manager:
            raise_validation(Code.Perm.DENIED, status_code=403, action="uncancel_event")

    _apply_status_transition(request, event, new_status, notify)

    # After a delete transition the event is gone — stop further processing
    if new_status == EventStatus.DELETED:
        return Status(200, _event_out(event, request.auth))

    return None
