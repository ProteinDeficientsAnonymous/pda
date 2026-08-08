from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.media_proxy import media_path
from django.db import transaction
from notifications.service import broadcast_event_update, create_waitlist_promoted_notifications
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._cohost_invite_helpers import get_my_pending_invite
from community._event_cohost_helpers import _pending_cohost_invites_out
from community._event_schemas import CancellationOut, EventOut, RSVPGuestOut, TagOut
from community._rsvp_counts import (
    _attending_headcount,
    _attending_headcount_db,
    _waitlisted_count,
)
from community._rsvp_payment import can_see_payment_details, payment_enforced_for_event
from community._shared import _authenticated_user, _gated
from community._validation import Code, raise_validation
from community.models import (
    Event,
    EventRSVP,
    EventTag,
    EventType,
    FeatureFlag,
    PageVisibility,
    RSVPStatus,
    SurveyQuestionType,
    flag_enabled,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


def load_event_with_stats_prefetch(event_id: UUID) -> Event | None:
    return (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .filter(id=event_id)
        .first()
    )


def broadcast_capacity_change(event_id: UUID, *, exclude_user_ids: set[str] | None = None) -> None:
    """Post-commit, silently refresh stakeholders' cached event so capacity shows live (no notification)."""
    excluded = exclude_user_ids or set()

    def _run() -> None:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .filter(id=event_id)
            .first()
        )
        if event is not None:
            broadcast_event_update(event, exclude_user_ids=excluded)

    transaction.on_commit(_run)


def is_cohost(requesting_user, co_host_ids: set[str]) -> bool:
    """Creator is always a co-host (added on event creation), so this covers both."""
    if requesting_user is None:
        return False
    return str(requesting_user.pk) in co_host_ids


_GUEST_LIST_STATUS_ORDER = {
    RSVPStatus.ATTENDING: 0,
    RSVPStatus.MAYBE: 1,
    RSVPStatus.CANT_GO: 2,
    RSVPStatus.WAITLISTED: 3,
}


def _build_guest_list(
    rsvps, can_see_phones: bool, viewer=None, can_see_payment_status: bool = False
) -> list[RSVPGuestOut]:
    """Build guest list ordered going > maybe > can't go > waitlisted, with optional phone
    and payment-status visibility."""
    ordered_rsvps = sorted(rsvps, key=lambda r: _GUEST_LIST_STATUS_ORDER.get(r.status, 99))
    return [
        RSVPGuestOut(
            user_id=str(r.user_id),
            name=visible_display_name(r.user, viewer),
            status=r.status,
            has_plus_one=r.has_plus_one,
            phone=r.user.phone_number if can_see_phones else None,
            photo_url=media_path(r.user.profile_photo),
            attendance=r.attendance,
            checked_in_at=r.checked_in_at,
            plus_one_attendance=r.plus_one_attendance,
            plus_one_checked_in_at=r.plus_one_checked_in_at,
            is_member=r.user.is_member,
            paid_confirmed=bool(r.paid_confirmed_at) if can_see_payment_status else False,
        )
        for r in ordered_rsvps
    ]


def _find_my_rsvp(rsvps, user):
    """Find requesting user's own RSVP row."""
    if user is None:
        return None
    for r in rsvps:
        if r.user_id == user.pk:
            return r
    return None


def _my_rsvp_fields(rsvps, user) -> tuple[str | None, bool]:
    """(my_rsvp status, my_paid_confirmed) for the requesting user, or (None, False)."""
    my_rsvp = _find_my_rsvp(rsvps, user)
    if my_rsvp is None:
        return None, False
    return my_rsvp.status, bool(my_rsvp.paid_confirmed_at)


_WITHIN_24_HOURS = timedelta(hours=24)


def _cancellations(event: Event, viewer=None) -> list[CancellationOut]:
    """Return currently-CANT_GO RSVPs with lead time (days before start).

    Lead time is derived from the recorded cancelled_at transition timestamp,
    falling back to updated_at for legacy rows that predate the column.
    within_24_hours compares the actual elapsed timedelta rather than
    truncated days, so a cancellation the day before doesn't misreport as
    "same day" just because day-truncation rounds it down to 0.
    Returns [] if the event has no start_datetime.
    """
    if event.start_datetime is None:
        return []
    rows = []
    for r in event.rsvps.all():
        if r.status != RSVPStatus.CANT_GO:
            continue
        cancelled_at = r.cancelled_at or r.updated_at
        lead_time = event.start_datetime - cancelled_at
        rows.append(
            CancellationOut(
                user_id=str(r.user_id),
                name=visible_display_name(r.user, viewer),
                cancelled_at=cancelled_at,
                days_before_event=lead_time.days,
                within_24_hours=timedelta(0) <= lead_time <= _WITHIN_24_HOURS,
                previous_status=r.previous_status,
            )
        )
    rows.sort(key=lambda x: x.cancelled_at, reverse=True)
    return rows


def _next_promotable_waitlist_rsvp(event: Event, headcount: int) -> EventRSVP | None:
    """Return the oldest waitlisted RSVP that still fits under max_attendees, if any."""
    oldest = (
        EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED)
        .order_by("created_at")
        .first()
    )
    if not oldest:
        return None
    if headcount + (2 if oldest.has_plus_one else 1) > event.max_attendees:
        return None
    return oldest


def promote_from_waitlist(event: Event) -> list[str]:
    """Promote oldest waitlisted users to attending (FIFO by created_at).

    Must be called inside a transaction.atomic() block with the event row locked.
    Returns the list of promoted user ids so callers that need to follow up per
    promoted user (e.g. emailing promoted non-members) can do so after commit.
    """
    if event.max_attendees is None:
        return []
    promoted_user_ids: list[str] = []
    unpaid_user_ids: list[str] = []
    needs_payment = payment_enforced_for_event(event)
    while True:
        headcount = _attending_headcount_db(event)
        if headcount >= event.max_attendees:
            break
        oldest = _next_promotable_waitlist_rsvp(event, headcount)
        if oldest is None:
            break
        oldest.status = RSVPStatus.ATTENDING
        oldest.save(update_fields=["status", "updated_at"])
        promoted_user_ids.append(str(oldest.user_id))
        if needs_payment and oldest.paid_confirmed_at is None:
            unpaid_user_ids.append(str(oldest.user_id))
    if promoted_user_ids:
        create_waitlist_promoted_notifications(event, promoted_user_ids, unpaid_user_ids)
    return promoted_user_ids


def _has_attendees(event: Event) -> bool:
    """Return True if the event has any invited users or attending RSVPs."""
    if event.invited_users.exists():
        return True
    return event.rsvps.filter(status=RSVPStatus.ATTENDING).exists()


def _can_see_invited(
    requesting_user,
    creator,
    co_host_ids: set[str],
) -> bool:
    """Check if requesting user can see invited users list.

    Hosts/co-hosts/admins only. Regular members — even when they're themselves
    invited — cannot see the list.
    """
    if requesting_user is None:
        return False
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    if str(requesting_user.pk) in co_host_ids:
        return True
    return requesting_user.has_permission(PermissionKey.MANAGE_EVENTS)


_INACTIVE_RSVP_STATUSES = {RSVPStatus.CANT_GO, RSVPStatus.REMOVED}


def _can_see_guests(requesting_user, viewer_is_cohost: bool, my_rsvp_status: str | None) -> bool:
    """Hosts, event managers, and active RSVPs can see the guest list.

    A cancelled (CANT_GO) or host-removed (REMOVED) RSVP row still exists, so
    my_rsvp_status is checked against active statuses rather than just None.
    """
    if requesting_user is None:
        return False
    if viewer_is_cohost or requesting_user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    return my_rsvp_status is not None and my_rsvp_status not in _INACTIVE_RSVP_STATUSES


def _can_see_invite_only(
    user, co_host_ids: set[str], invited_user_ids: set[str], created_by_id
) -> bool:
    """Check if user can see an invite-only event (using prefetched sets)."""
    if user is None:
        return False
    if created_by_id is not None and str(user.pk) == str(created_by_id):
        return True
    if str(user.pk) in co_host_ids:
        return True
    if str(user.pk) in invited_user_ids:
        return True
    return user.has_permission(PermissionKey.MANAGE_EVENTS)


def _get_creator_name(creator, viewer=None) -> str | None:
    if creator is None:
        return None
    return visible_display_name(creator, viewer)


def _tags_out(event: Event) -> list[TagOut]:
    """Serialize an event's tags (uses the prefetched `tags` relation)."""
    return [TagOut(id=str(t.id), name=t.name, slug=t.slug) for t in event.tags.all()]


def _set_event_tags(event: Event, tag_ids: Iterable[str]) -> None:
    """Replace an event's tags with the curated tags matching `tag_ids`.

    Unknown ids are silently dropped — the tag set is admin-curated, so a stale
    or invalid id from a client just means "no such tag", not an error worth
    failing the whole save over.
    """
    tags = EventTag.objects.filter(pk__in=list(tag_ids))
    event.tags.set(tags)


def _get_datetime_poll_slug(event: Event) -> str | None:
    poll_survey = (
        event.surveys.filter(
            is_active=True,
            questions__field_type=SurveyQuestionType.DATETIME_POLL,
        )
        .values_list("slug", flat=True)
        .first()
    )
    return poll_survey


def _resolve_comment_count(event: Event) -> int:
    """Read the annotated comment_count, falling back to a per-event count query."""
    annotated = getattr(event, "comment_count", None)
    if annotated is not None:
        return annotated
    return event.comments.filter(deleted_at__isnull=True).count()


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


def _event_out(event: Event, requesting_user=None) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    auth_user = _authenticated_user(requesting_user)
    is_authed = auth_user is not None
    show_payment_details = can_see_payment_details(event, is_authed)
    co_host_ids = {str(u.id) for u in co_hosts}
    viewer_is_cohost = is_cohost(auth_user, co_host_ids)
    payment_status_visible = viewer_is_cohost and flag_enabled(
        FeatureFlag.EVENT_PAYMENT_CONFIRMATION
    )
    all_rsvps = list(event.rsvps.all()) if event.rsvp_enabled else []
    all_invited = list(event.invited_users.all())
    invited = all_invited if _can_see_invited(auth_user, creator, co_host_ids) else []

    pending_invites_out = _pending_cohost_invites_out(event, auth_user, co_host_ids)
    my_pending_invite = get_my_pending_invite(event, auth_user)
    my_pending_invite_id = str(my_pending_invite.id) if my_pending_invite else None
    comment_count = _resolve_comment_count(event)
    my_rsvp_status, my_paid_confirmed = _my_rsvp_fields(all_rsvps, auth_user)
    can_see_guests = _can_see_guests(auth_user, viewer_is_cohost, my_rsvp_status)
    return EventOut(
        id=str(event.id),
        slug=event.slug,
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        latitude=float(event.latitude) if event.latitude is not None else None,
        longitude=float(event.longitude) if event.longitude is not None else None,
        whatsapp_link=_gated(event.whatsapp_link, "", is_authed),
        partiful_link=_gated(event.partiful_link, "", is_authed),
        other_link=_gated(event.other_link, "", is_authed),
        price=event.price,
        venmo_link=_gated(event.venmo_link, "", show_payment_details),
        cashapp_link=_gated(event.cashapp_link, "", show_payment_details),
        zelle_info=_gated(event.zelle_info, "", show_payment_details),
        rsvp_enabled=event.rsvp_enabled,
        datetime_tbd=event.datetime_tbd,
        allow_plus_ones=event.allow_plus_ones,
        max_attendees=event.max_attendees,
        attending_count=_attending_headcount(event),
        waitlisted_count=_waitlisted_count(event),
        invited_count=len(all_invited),
        comment_count=comment_count,
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=_get_creator_name(creator, auth_user),
        created_by_photo_url=media_path(creator.profile_photo) if creator else "",
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[visible_display_name(u, auth_user) for u in co_hosts],
        co_host_photo_urls=[media_path(u.profile_photo) for u in co_hosts],
        guests=_gated(
            _build_guest_list(all_rsvps, viewer_is_cohost, auth_user, payment_status_visible),
            [],
            can_see_guests,
        ),
        my_rsvp=my_rsvp_status,
        my_paid_confirmed=my_paid_confirmed,
        viewer_user_id=str(auth_user.pk) if auth_user else None,
        event_type=event.event_type,
        visibility=event.visibility,
        photo_url=media_path(event.photo),
        photo_updated_at=_iso_or_none(event.photo_updated_at),
        survey_slugs=list(event.surveys.filter(is_active=True).values_list("slug", flat=True)),
        datetime_poll_slug=_get_datetime_poll_slug(event),
        has_poll=hasattr(event, "poll"),
        invited_user_ids=[str(u.id) for u in invited],
        invited_user_names=[visible_display_name(u, auth_user) for u in invited],
        invited_user_photo_urls=[media_path(u.profile_photo) for u in invited],
        invite_permission=event.invite_permission,
        is_past=event.is_past,
        status=event.status,
        pending_cohost_invites=pending_invites_out,
        my_pending_cohost_invite_id=my_pending_invite_id,
        tags=_tags_out(event),
    )


def _can_edit_event(user, event: Event) -> bool:
    """Check if user can edit/delete this event (host or manager)."""
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    return event.co_hosts.filter(pk=user.pk).exists()


_PUBLIC_ONLY_TYPES = frozenset({EventType.OFFICIAL, EventType.CLUB})

# Event types that require an explicit permission to tag. Community events need
# none. Maps type → the permission that gates it.
_TYPE_TAG_PERMISSIONS = {
    EventType.OFFICIAL: PermissionKey.TAG_OFFICIAL_EVENT,
    EventType.CLUB: PermissionKey.TAG_CLUB_EVENT,
}


def _is_invalid_typed_visibility(event_type: str, visibility: str) -> bool:
    """Public-only event types (official, club) must have public visibility."""
    return event_type in _PUBLIC_ONLY_TYPES and visibility != PageVisibility.PUBLIC


def _enforce_type_tag_permission(request, event_type: str, endpoint: str, event_id=None) -> None:
    """Raise 403 if the event type requires a tag permission the user lacks."""
    required = _TYPE_TAG_PERMISSIONS.get(event_type)
    if required is None or request.auth.has_permission(required):
        return
    details = {"endpoint": endpoint, "required_permission": required}
    if event_id is not None:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(type=AuditTargetType.EVENT, id=str(event_id), details=details),
        )
    else:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(details=details),
        )
    raise_validation(Code.Perm.DENIED, status_code=403, action=required)
