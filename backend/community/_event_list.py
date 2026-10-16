from django.db.models import Count, Prefetch, Q
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._event_helpers import (
    _float_or_none,
    _get_creator_name,
    _iso_or_none,
    _my_rsvp_fields,
    _tags_out,
    _viewer_rsvp_rows,
)
from community._event_schemas import EventListOut
from community._rsvp_counts import (
    attending_count_annotation,
    waitlisted_count_annotation,
)
from community._rsvp_payment import can_see_payment_details
from community._shared import _gated
from community._tentative_member_access import (
    event_viewer_for,
    is_tentative_member,
    tentative_member_event_q,
)
from community.models import Event, EventRSVP, EventStatus, PageVisibility


def _list_rsvp_prefetch(auth_user):
    """Viewer RSVP only, on `_viewer_rsvps` so `event.rsvps` is not a filtered cache."""
    qs = EventRSVP.objects.none()
    if auth_user is not None:
        qs = EventRSVP.objects.filter(user=auth_user)
    return Prefetch("rsvps", queryset=qs, to_attr="_viewer_rsvps")


def _list_count_annotations():
    return {
        "comment_count": Count(
            "comments",
            filter=Q(comments__deleted_at__isnull=True),
            distinct=True,
        ),
        "attending_count": attending_count_annotation(),
        "waitlisted_count": waitlisted_count_annotation(),
    }


def _build_events_queryset(status: str, auth_user, is_authed):
    """Build the events queryset for list_events based on status and auth state."""
    related = ["co_hosts", "poll", "tags", _list_rsvp_prefetch(auth_user)]
    if status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return (
            Event.objects.select_related("created_by")
            .prefetch_related(*related)
            .annotate(**_list_count_annotations())
            .filter(status=status)
            .filter(Q(created_by=auth_user) | Q(co_hosts=auth_user))
            .distinct()
        )
    qs = (
        Event.objects.select_related("created_by")
        .prefetch_related(*related)
        .annotate(**_list_count_annotations())
        .filter(status=EventStatus.ACTIVE)
    )
    if not is_authed:
        qs = qs.filter(visibility=PageVisibility.PUBLIC)
    elif is_tentative_member(auth_user):
        qs = qs.filter(tentative_member_event_q())
    return qs


def _filter_invite_only(events, auth_user, status: str):
    """Restrict invite-only rows in SQL so list_events never hydrates invitees."""
    if not auth_user or status in (EventStatus.CANCELLED, EventStatus.DRAFT):
        return events
    if auth_user.has_permission(PermissionKey.MANAGE_EVENTS):
        return events
    return events.filter(
        ~Q(visibility=PageVisibility.INVITE_ONLY)
        | Q(created_by=auth_user)
        | Q(co_hosts=auth_user)
        | Q(invited_users=auth_user)
    ).distinct()


def _event_list_out(e, auth_user, is_authed: bool) -> EventListOut:
    auth_user = event_viewer_for(auth_user, e)
    is_authed = is_authed and auth_user is not None
    show_payment_details = can_see_payment_details(e, is_authed)
    my_rsvp_status, my_paid_confirmed = _my_rsvp_fields(_viewer_rsvp_rows(e, auth_user), auth_user)
    co_hosts = list(e.co_hosts.all())
    return EventListOut(
        id=str(e.id),
        slug=e.slug,
        title=e.title,
        description=e.description,
        start_datetime=e.start_datetime,
        end_datetime=e.end_datetime,
        location=_gated(e.location, "", is_authed),
        latitude=_gated(_float_or_none(e.latitude), None, is_authed),
        longitude=_gated(_float_or_none(e.longitude), None, is_authed),
        event_type=e.event_type,
        visibility=e.visibility,
        # Calendar/My Events never render these; skip media_path to avoid per-row presigns.
        photo_url="",
        photo_updated_at=_iso_or_none(e.photo_updated_at),
        whatsapp_link=_gated(e.whatsapp_link, "", is_authed),
        partiful_link=_gated(e.partiful_link, "", is_authed),
        other_link=_gated(e.other_link, "", is_authed),
        price=e.price,
        venmo_link=_gated(e.venmo_link, "", show_payment_details),
        cashapp_link=_gated(e.cashapp_link, "", show_payment_details),
        zelle_info=_gated(e.zelle_info, "", show_payment_details),
        created_by_id=str(e.created_by_id) if e.created_by_id else None,
        created_by_name=_get_creator_name(e.created_by, auth_user),
        created_by_photo_url="",
        co_host_photo_urls=[],
        datetime_tbd=e.datetime_tbd,
        has_poll=hasattr(e, "poll"),
        allow_plus_ones=e.allow_plus_ones,
        max_attendees=e.max_attendees,
        attending_count=e.attending_count,
        waitlisted_count=e.waitlisted_count,
        invited_count=0,  # host-only; filled on event detail, not the calendar list
        comment_count=e.comment_count,
        my_rsvp=my_rsvp_status,
        my_paid_confirmed=my_paid_confirmed,
        co_host_ids=[str(c.id) for c in co_hosts],
        co_host_names=[visible_display_name(c, auth_user) for c in co_hosts],
        is_past=e.is_past,
        status=e.status,
        is_partiful_import=e.is_partiful_import,
        is_legacy=e.is_legacy,
        tags=_tags_out(e),
    )
