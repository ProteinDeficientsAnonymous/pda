import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone

from community._event_helpers import (
    _can_edit_event,
    _enforce_type_tag_permission,
    _is_invalid_typed_visibility,
    _set_event_tags,
    _update_co_hosts,
    promote_from_waitlist,
)
from community._validation import Code, raise_validation
from community.models import Event


def _validate_event_datetimes(start, end, datetime_tbd: bool, *, check_past: bool = True) -> None:
    """Raise ValidationException if datetime fields are invalid."""
    if start is None:
        if not datetime_tbd:
            raise_validation(Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD, field="start_datetime")
        return
    if end is not None and end <= start:
        raise_validation(Code.Event.END_BEFORE_START, field="end_datetime")
    if check_past and not datetime_tbd and start < timezone.now():
        raise_validation(Code.Event.START_DATETIME_MUST_BE_FUTURE, field="start_datetime")


def _validate_update_payload(request, event: Event, event_id, updates: dict) -> None:
    """Validate PATCH payload fields. Raises ValidationException on failure."""
    if "event_type" in updates:
        _enforce_type_tag_permission(request, updates["event_type"], "update_event", event_id)
    effective_type = updates.get("event_type", event.event_type)
    effective_visibility = updates.get("visibility", event.visibility)
    if _is_invalid_typed_visibility(effective_type, effective_visibility):
        raise_validation(Code.Event.OFFICIAL_MUST_BE_PUBLIC, status_code=400)
    # While a poll is active, the poll is the source of truth for when. Block
    # direct edits to start/end so the event time can't drift from the poll.
    # Host must finalize (or delete) the poll before setting a time.
    time_fields_edited = any(
        f in updates for f in ("start_datetime", "end_datetime", "datetime_tbd")
    )
    if time_fields_edited and hasattr(event, "poll") and event.poll.is_active:
        raise_validation(Code.Event.DATE_LOCKED_BY_POLL, status_code=400)
    effective_start = updates.get("start_datetime", event.start_datetime)
    effective_end = updates.get("end_datetime", event.end_datetime)
    effective_tbd = updates.get("datetime_tbd", event.datetime_tbd)
    # Drafts can legitimately have no start yet (see #357) — don't enforce
    # "start required" or past-check when a draft stays dateless. But if the
    # draft has a start (existing or being set), it must be a future date.
    if event.is_draft and effective_start is None:
        return
    # Past-check applies when start_datetime is being touched, or on any
    # edit to a draft that already has a start (stale-draft guard). Non-
    # draft past events keep being tweakable for non-date fields within
    # the 6-hour grace window (enforced client-side).
    check_past = "start_datetime" in updates or event.is_draft
    _validate_event_datetimes(effective_start, effective_end, effective_tbd, check_past=check_past)


def _promote_if_capacity_increased(
    event: Event, updates: dict, old_max_attendees: int | None
) -> list[str]:
    """Promote waitlisted users if `max_attendees` grew. Must run inside the locked transaction."""
    capacity_increased = (
        "max_attendees" in updates
        and event.max_attendees is not None
        and (old_max_attendees is None or event.max_attendees > old_max_attendees)
    )
    if not capacity_increased:
        return []
    return promote_from_waitlist(event)


def _guard_can_edit_event(request, event: Event, event_id: UUID) -> None:
    if _can_edit_event(request.auth, event):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(
            type=AuditTargetType.EVENT, id=str(event_id), details={"endpoint": "update_event"}
        ),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action="update_event")


def _apply_field_updates(request, event: Event, event_id: UUID, updates: dict) -> None:
    """Apply non-status field edits to an event. Raises ValidationException on failure."""
    if not updates:
        return
    if "max_attendees" in updates:
        # Lock the row so a concurrent capacity-based promotion can't race this edit.
        Event.objects.select_for_update().get(id=event_id)
    _validate_update_payload(request, event, event_id, updates)
    co_host_ids = updates.pop("co_host_ids", None)
    tag_ids = updates.pop("tag_ids", None)
    changed_fields = list(updates.keys())
    if co_host_ids is not None:
        changed_fields.append("co_host_ids")
    if tag_ids is not None:
        changed_fields.append("tag_ids")
    for field, value in updates.items():
        setattr(event, field, value)
    if co_host_ids is not None:
        _update_co_hosts(event, co_host_ids, request.auth)
    if tag_ids is not None:
        _set_event_tags(event, tag_ids)
    event.save()
    audit_log(
        logging.INFO,
        "event_updated",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT, id=str(event_id), details={"fields_changed": changed_fields}
        ),
    )
