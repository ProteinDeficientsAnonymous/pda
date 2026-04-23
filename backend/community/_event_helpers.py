"""Helper functions for event output serialization and visibility checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.media_proxy import media_path
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._event_schemas import EventOut, RSVPGuestOut
from community._shared import _authenticated_user, _members_only
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus, SurveyQuestionType

if TYPE_CHECKING:
    from collections.abc import Iterable


def _can_see_phones(requesting_user, creator, co_host_ids: set[str]) -> bool:
    """Check if requesting user can see guest phone numbers."""
    if requesting_user is None:
        return False
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    return str(requesting_user.pk) in co_host_ids


def _build_guest_list(rsvps, can_see_phones: bool) -> list[RSVPGuestOut]:
    """Build guest list with optional phone visibility."""
    return [
        RSVPGuestOut(
            user_id=str(r.user_id),
            name=r.user.display_name or r.user.phone_number,
            status=r.status,
            has_plus_one=r.has_plus_one,
            phone=r.user.phone_number if can_see_phones else None,
            photo_url=media_path(r.user.profile_photo),
            attendance=r.attendance,
        )
        for r in rsvps
    ]


def _find_my_rsvp(rsvps, user) -> str | None:
    """Find requesting user's RSVP status."""
    if user is None:
        return None
    for r in rsvps:
        if r.user_id == user.pk:
            return r.status
    return None


def _attending_headcount(event: Event) -> int:
    """Count attending spots from prefetched RSVPs (each attendee + their +1)."""
    return sum(
        1 + (1 if r.has_plus_one else 0)
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING
    )


def _attending_headcount_db(event: Event, exclude_user=None) -> int:
    """Count attending spots via DB query (use inside select_for_update transactions)."""
    from django.db.models import Case, IntegerField, Sum, Value, When

    qs = EventRSVP.objects.filter(event=event, status=RSVPStatus.ATTENDING)
    if exclude_user is not None:
        qs = qs.exclude(user=exclude_user)
    result = qs.aggregate(
        total=Sum(
            Case(
                When(has_plus_one=True, then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
    )
    return result["total"] or 0


def _waitlisted_count(event: Event) -> int:
    """Count waitlisted RSVPs from prefetched data."""
    return sum(1 for r in event.rsvps.all() if r.status == RSVPStatus.WAITLISTED)


def _maybe_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if r.status == RSVPStatus.MAYBE)


def _cant_go_count(event: Event) -> int:
    return sum(1 for r in event.rsvps.all() if r.status == RSVPStatus.CANT_GO)


def _no_response_count(event: Event) -> int:
    """Invited users who have no RSVP row."""
    responded = {r.user_id for r in event.rsvps.all()}
    return sum(1 for u in event.invited_users.all() if u.pk not in responded)


def _attended_count(event: Event) -> int:
    return sum(
        1
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING and r.attendance == AttendanceStatus.ATTENDED
    )


def _no_show_count(event: Event) -> int:
    return sum(
        1
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING and r.attendance == AttendanceStatus.NO_SHOW
    )


def _not_marked_count(event: Event) -> int:
    return sum(
        1
        for r in event.rsvps.all()
        if r.status == RSVPStatus.ATTENDING and r.attendance == AttendanceStatus.UNKNOWN
    )


def _cancellations(event: Event) -> list[dict]:
    """Return currently-CANT_GO RSVPs with inferred lead time (days before start).

    Lossy for users who flipped between statuses — uses updated_at as proxy.
    Returns [] if the event has no start_datetime.
    """
    if event.start_datetime is None:
        return []
    rows = [
        {
            "user_id": str(r.user_id),
            "name": r.user.display_name or r.user.phone_number,
            "cancelled_at": r.updated_at,
            "days_before_event": (event.start_datetime - r.updated_at).days,
        }
        for r in event.rsvps.all()
        if r.status == RSVPStatus.CANT_GO
    ]
    rows.sort(key=lambda x: x["cancelled_at"], reverse=True)
    return rows


def promote_from_waitlist(event: Event) -> None:
    """Promote oldest waitlisted users to attending (FIFO by created_at).

    Must be called inside a transaction.atomic() block with the event row locked.
    """
    from notifications.service import create_waitlist_promoted_notifications

    if event.max_attendees is None:
        return
    promoted_user_ids: list[str] = []
    while True:
        headcount = _attending_headcount_db(event)
        if headcount >= event.max_attendees:
            break
        oldest = (
            EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED)
            .order_by("created_at")
            .first()
        )
        if not oldest:
            break
        oldest.status = RSVPStatus.ATTENDING
        oldest.save(update_fields=["status", "updated_at"])
        promoted_user_ids.append(str(oldest.user_id))
    if promoted_user_ids:
        create_waitlist_promoted_notifications(event, promoted_user_ids)


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


def _get_creator_name(creator) -> str | None:
    if creator is None:
        return None
    return creator.display_name or creator.phone_number


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


def _event_out(event: Event, requesting_user=None) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    auth_user = _authenticated_user(requesting_user)
    is_authed = auth_user is not None
    co_host_ids = {str(u.id) for u in co_hosts}
    phones_visible = _can_see_phones(auth_user, creator, co_host_ids)
    rsvps = list(event.rsvps.all()) if (event.rsvp_enabled and is_authed) else []
    all_invited = list(event.invited_users.all())
    invited = all_invited if _can_see_invited(auth_user, creator, co_host_ids) else []
    return EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        latitude=float(event.latitude) if event.latitude is not None else None,
        longitude=float(event.longitude) if event.longitude is not None else None,
        whatsapp_link=_members_only(event.whatsapp_link, "", is_authed),
        partiful_link=_members_only(event.partiful_link, "", is_authed),
        other_link=_members_only(event.other_link, "", is_authed),
        price=event.price,
        venmo_link=_members_only(event.venmo_link, "", is_authed),
        cashapp_link=_members_only(event.cashapp_link, "", is_authed),
        zelle_info=_members_only(event.zelle_info, "", is_authed),
        rsvp_enabled=_members_only(event.rsvp_enabled, False, is_authed),
        datetime_tbd=event.datetime_tbd,
        allow_plus_ones=event.allow_plus_ones,
        max_attendees=event.max_attendees,
        attending_count=_attending_headcount(event),
        waitlisted_count=_waitlisted_count(event),
        invited_count=len(all_invited),
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=_get_creator_name(creator),
        created_by_photo_url=media_path(creator.profile_photo) if creator else "",
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[u.display_name or u.phone_number for u in co_hosts],
        co_host_photo_urls=[media_path(u.profile_photo) for u in co_hosts],
        guests=_members_only(_build_guest_list(rsvps, phones_visible), [], is_authed),
        my_rsvp=_find_my_rsvp(rsvps, auth_user),
        event_type=event.event_type,
        visibility=event.visibility,
        photo_url=media_path(event.photo),
        survey_slugs=list(event.surveys.filter(is_active=True).values_list("slug", flat=True)),
        datetime_poll_slug=_get_datetime_poll_slug(event),
        has_poll=hasattr(event, "poll"),
        invited_user_ids=[str(u.id) for u in invited],
        invited_user_names=[u.display_name or u.phone_number for u in invited],
        invited_user_photo_urls=[media_path(u.profile_photo) for u in invited],
        invite_permission=event.invite_permission,
        is_past=event.is_past,
        status=event.status,
    )


def _update_co_hosts(
    event: Event,
    co_host_ids: Iterable[str],
    updater: UserModel,
) -> None:
    """Update event.co_hosts and notify newly added co-hosts."""
    from notifications.service import broadcast_event_update, create_cohost_added_notifications

    old_ids = {str(uid) for uid in event.co_hosts.values_list("pk", flat=True)}
    next_ids = {str(uid) for uid in co_host_ids}
    co_hosts = UserModel.objects.filter(pk__in=co_host_ids)
    event.co_hosts.set(co_hosts)
    new_ids = next_ids - old_ids
    if new_ids:
        create_cohost_added_notifications(event, new_ids, updater)
    # Silent live-update ping for anyone already viewing the event — so removed
    # co-hosts and other stakeholders see the change without needing to reload.
    # Exclude the updater (their local cache is already up-to-date).
    if old_ids != next_ids:
        removed_ids = old_ids - next_ids
        broadcast_event_update(
            event,
            exclude_user_ids={str(updater.pk)},
            extra_user_ids=removed_ids,
        )


def _update_invited_users(
    event: Event,
    invited_user_ids: Iterable[str],
    inviter: UserModel,
) -> None:
    """Update event.invited_users and notify newly added users."""
    from notifications.service import create_event_invite_notifications

    id_list = list(invited_user_ids)
    old_ids = set(event.invited_users.values_list("pk", flat=True))
    invited = UserModel.objects.filter(pk__in=id_list)
    event.invited_users.set(invited)
    new_ids = {str(uid) for uid in id_list} - {str(uid) for uid in old_ids}
    if new_ids:
        create_event_invite_notifications(event, new_ids, inviter)
