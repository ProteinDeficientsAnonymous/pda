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
from community._validation import Code, raise_validation
from community.models import Event, EventStatus


def _cancel_event(request, event: Event, notify: bool) -> None:
    """ACTIVE → CANCELLED. Raises ValidationException on failure."""
    if event.is_past:
        raise_validation(Code.Event.PAST_CANNOT_BE_CANCELLED, status_code=400)
    if not _has_attendees(event):
        raise_validation(Code.Event.NO_ATTENDEES_CANNOT_BE_CANCELLED, status_code=400)
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


def _delete_event(request, event: Event) -> None:
    """ACTIVE|CANCELLED|DRAFT → DELETED. Raises ValidationException on failure."""
    if event.status == EventStatus.ACTIVE and not event.is_past and _has_attendees(event):
        raise_validation(Code.Event.CANCEL_BEFORE_DELETE, status_code=400)
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


def _apply_status_transition(request, event: Event, new_status: str, notify: bool) -> None:
    """Validate and apply a status transition. Raises ValidationException on failure."""
    current = event.status
    if current == new_status:
        return
    if current == EventStatus.DRAFT and new_status == EventStatus.ACTIVE:
        _publish_draft(request, event)
        return
    if new_status == EventStatus.DELETED and current in (
        EventStatus.DRAFT,
        EventStatus.ACTIVE,
        EventStatus.CANCELLED,
    ):
        _delete_event(request, event)
        return
    if current == EventStatus.ACTIVE and new_status == EventStatus.CANCELLED:
        _cancel_event(request, event, notify)
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
    # Uncancel requires creator/manager — co-hosts cannot uncancel
    if new_status == EventStatus.ACTIVE and event.is_cancelled:
        is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
        is_creator = event.created_by_id == request.auth.pk
        if not is_creator and not is_manager:
            raise_validation(Code.Perm.DENIED, status_code=403, action="uncancel_event")

    _apply_status_transition(request, event, new_status, notify)

    # After a delete transition the event is gone — stop further processing
    if new_status == EventStatus.DELETED:
        from community._event_helpers import _event_out

        return Status(200, _event_out(event, request.auth))

    return None
