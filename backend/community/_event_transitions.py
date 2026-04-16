"""Status transition helpers for Event lifecycle changes."""

import logging

from config.audit import audit_log
from django.utils import timezone
from ninja.responses import Status
from notifications.service import (
    create_cohost_added_notifications,
    create_event_invite_notifications,
)
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._event_helpers import _has_attendees
from community._shared import ErrorOut
from community.models import Event, EventStatus


def _cancel_event(request, event: Event, notify: bool) -> str | None:
    """ACTIVE → CANCELLED. Returns error string or None."""
    if event.is_past:
        return "Past events cannot be cancelled — use delete instead."
    if not _has_attendees(event):
        return "Events with no invited users or RSVPs cannot be cancelled — use delete instead."
    event.status = EventStatus.CANCELLED
    event.save(update_fields=["status"])
    if notify:
        from notifications.service import create_event_cancellation_notifications

        create_event_cancellation_notifications(event, request.auth)
    audit_log(
        logging.INFO,
        "event_cancelled",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"title": event.title, "notify_attendees": notify},
    )
    return None


def _delete_event(request, event: Event) -> str | None:
    """ACTIVE|CANCELLED|DRAFT → DELETED. Returns error string or None."""
    if event.status == EventStatus.ACTIVE and not event.is_past and _has_attendees(event):
        return "Cancel this event before deleting it."
    event.status = EventStatus.DELETED
    event.deleted_at = timezone.now()
    event.save(update_fields=["status", "deleted_at"])
    audit_log(
        logging.INFO,
        "event_deleted",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"title": event.title},
    )
    return None


def _uncancel_event(request, event: Event) -> None:
    """CANCELLED → ACTIVE. Permission check is the caller's responsibility."""
    event.status = EventStatus.ACTIVE
    event.save(update_fields=["status"])
    audit_log(
        logging.INFO,
        "event_uncancelled",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"title": event.title},
    )


def _set_event_participants(
    request, event: Event, co_host_ids: list, invited_user_ids: list
) -> None:
    """Attach co-hosts and invitees to the event and send appropriate notifications."""
    if co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=co_host_ids)
        event.co_hosts.set(co_hosts)
        # Cohosts are notified immediately, even on drafts — they're collaborators.
        create_cohost_added_notifications(event, co_host_ids, request.auth)
    if invited_user_ids:
        invited = UserModel.objects.filter(pk__in=invited_user_ids)
        event.invited_users.set(invited)
        # Invitee notifications are deferred until the draft is published.
        if not event.is_draft:
            create_event_invite_notifications(event, invited_user_ids, request.auth)


def _publish_draft(request, event: Event) -> str | None:
    """DRAFT → ACTIVE. Re-validates dates, fires invitee notifications, audit logs."""
    if not event.datetime_tbd and event.start_datetime < timezone.now():
        return "Start date must be in the future to publish."
    event.status = EventStatus.ACTIVE
    event.save(update_fields=["status"])
    invited_ids = [str(u.id) for u in event.invited_users.all()]
    if invited_ids:
        create_event_invite_notifications(event, invited_ids, request.auth)
    audit_log(
        logging.INFO,
        "event_published",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"title": event.title},
    )
    return None


def _apply_status_transition(request, event: Event, new_status: str, notify: bool) -> str | None:
    """Validate and apply a status transition. Returns an error message or None on success."""
    current = event.status
    if current == EventStatus.DRAFT and new_status == EventStatus.ACTIVE:
        return _publish_draft(request, event)
    if current == EventStatus.DRAFT and new_status == EventStatus.DELETED:
        return _delete_event(request, event)
    if current == EventStatus.ACTIVE and new_status == EventStatus.CANCELLED:
        return _cancel_event(request, event, notify)
    if current in (EventStatus.ACTIVE, EventStatus.CANCELLED) and new_status == EventStatus.DELETED:
        return _delete_event(request, event)
    if current == EventStatus.CANCELLED and new_status == EventStatus.ACTIVE:
        _uncancel_event(request, event)
        return None
    return f"Invalid status transition: {current} → {new_status}."


def _handle_status_update(request, event: Event, new_status: str, notify: bool):
    """
    Validate and apply a status transition from update_event.
    Returns a Status response to send immediately, or None to continue processing field edits.
    """
    # Uncancel requires creator/manager — co-hosts cannot uncancel
    if new_status == EventStatus.ACTIVE and event.is_cancelled:
        is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
        is_creator = event.created_by_id == request.auth.pk
        if not is_creator and not is_manager:
            return Status(403, ErrorOut(detail="Permission denied."))

    err = _apply_status_transition(request, event, new_status, notify)
    if err is not None:
        return Status(400, ErrorOut(detail=err))

    # After a delete transition the event is gone — stop further processing
    if new_status == EventStatus.DELETED:
        from community._event_helpers import _event_out

        return Status(200, _event_out(event, request.auth))

    return None
