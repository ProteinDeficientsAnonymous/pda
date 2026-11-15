import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.utils import timezone

from community.cohosts.helpers import update_co_hosts
from community.events._field_validators import check_rsvp_deadline
from community.events.helpers import (
    can_edit_event,
    enforce_type_tag_permission,
    is_invalid_typed_visibility,
    set_event_tags,
    validated_event_format,
)
from community.models import Event, EventSlugAlias, EventType, is_official_or_club
from community.models.event_slug import RESERVED_EVENT_SLUGS, rename_event_slug
from community.rsvps.waitlist import promote_from_waitlist
from community.validation import Code, raise_validation


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
        enforce_type_tag_permission(request, updates["event_type"], "update_event", event_id)
    effective_type = updates.get("event_type", event.event_type)
    effective_visibility = updates.get("visibility", event.visibility)
    if is_invalid_typed_visibility(effective_type, effective_visibility):
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


def _validate_rsvp_deadline_update(event: Event, updates: dict) -> None:
    if not any(f in updates for f in ("rsvp_deadline", "start_datetime", "datetime_tbd")):
        return
    check_rsvp_deadline(
        updates.get("rsvp_deadline", event.rsvp_deadline),
        updates.get("start_datetime", event.start_datetime),
        updates.get("datetime_tbd", event.datetime_tbd),
    )


def promote_if_capacity_increased(
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


def _lock_typed_plus_ones(event: Event, updates: dict) -> None:
    """Older official/club events keep +1s until turned off; nothing can turn them back on."""
    new_type = updates.get("event_type", event.event_type)
    if not is_official_or_club(new_type):
        return
    turning_on = updates.get("allow_plus_ones") and not event.allow_plus_ones
    if turning_on or new_type != event.event_type:
        updates["allow_plus_ones"] = False


def _resolve_event_format(event: Event, updates: dict) -> None:
    """Treat a null format as unchanged, and clear the format when the event stops being official."""
    effective_type = updates.get("event_type", event.event_type)
    validated_event_format(updates.get("event_format"), effective_type)
    if updates.get("event_format", "") is None:
        del updates["event_format"]
    if effective_type != EventType.OFFICIAL and event.event_format:
        updates["event_format"] = ""


def guard_can_edit_event(request, event: Event, event_id: UUID) -> None:
    if can_edit_event(request.auth, event):
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


def _is_event_slug_taken(slug: str, event_pk) -> bool:
    """True if `slug` is reserved, or is another event's current or renamed-from slug."""
    if slug in RESERVED_EVENT_SLUGS:
        return True
    if Event.objects.filter(slug=slug).exclude(pk=event_pk).exists():
        return True
    return EventSlugAlias.objects.filter(slug=slug).exclude(event_id=event_pk).exists()


def _apply_slug_update(event: Event, updates: dict) -> None:
    new_slug = updates.pop("slug", None)
    if new_slug is None or new_slug == event.slug:
        return
    if _is_event_slug_taken(new_slug, event.pk):
        raise_validation(Code.Event.SLUG_TAKEN, field="slug", status_code=409)
    rename_event_slug(event, new_slug)


def apply_field_updates(request, event: Event, event_id: UUID, updates: dict) -> None:
    """Apply non-status field edits to an event. Raises ValidationException on failure."""
    if not updates:
        return
    if "max_attendees" in updates:
        # Lock the row so a concurrent capacity-based promotion can't race this edit.
        Event.objects.select_for_update().get(id=event_id)
    _validate_update_payload(request, event, event_id, updates)
    _validate_rsvp_deadline_update(event, updates)
    _lock_typed_plus_ones(event, updates)
    _resolve_event_format(event, updates)
    co_host_ids = updates.pop("co_host_ids", None)
    tag_ids = updates.pop("tag_ids", None)
    changed_fields = list(updates.keys())
    _apply_slug_update(event, updates)
    if co_host_ids is not None:
        changed_fields.append("co_host_ids")
    if tag_ids is not None:
        changed_fields.append("tag_ids")
    for field, value in updates.items():
        setattr(event, field, value)
    if co_host_ids is not None:
        update_co_hosts(event, co_host_ids, request.auth)
    if tag_ids is not None:
        set_event_tags(event, tag_ids)
    event.save()
    audit_log(
        logging.INFO,
        "event_updated",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT, id=str(event_id), details={"fields_changed": changed_fields}
        ),
    )
