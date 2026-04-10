"""Events CRUD and event photo endpoints."""

import logging
import time
from uuid import UUID

from config.audit import audit_log
from config.media_proxy import media_path
from config.ratelimit import rate_limit
from django.db.models import Q
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.service import (
    create_cohost_added_notifications,
    create_event_invite_notifications,
)
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._event_helpers import (
    _can_see_invite_only,
    _event_out,
    _update_co_hosts,
    _update_invited_users,
)
from community._event_schemas import (
    _ALLOWED_IMAGE_TYPES,
    _MAX_EVENT_PHOTO_SIZE,
    EventIn,
    EventListOut,
    EventOut,
    EventPatchIn,
)
from community._shared import ErrorOut, _authenticated_user, _members_only, _optional_jwt
from community.models import (
    Event,
    EventStatus,
    EventType,
    PageVisibility,
)

router = Router()


def _can_edit_event(user, event: Event) -> bool:
    """Check if user can edit/delete this event (creator, co-host, or manager)."""
    if user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if event.created_by_id == user.pk:
        return True
    return event.co_hosts.filter(pk=user.pk).exists()


def _is_invalid_official_visibility(event_type: str, visibility: str) -> bool:
    """Official events must have public visibility."""
    return event_type == EventType.OFFICIAL and visibility != PageVisibility.PUBLIC


def _validate_event_datetimes(
    start, end, datetime_tbd: bool, *, check_past: bool = True
) -> str | None:
    """Return an error message if datetime fields are invalid, else None."""
    if end is not None and end <= start:
        return "end_datetime must be after start_datetime."
    if check_past and not datetime_tbd and start < timezone.now():
        return "Start date must be in the future."
    return None


def _validate_update_payload(request, event: Event, event_id, updates: dict) -> Status | None:
    """Validate PATCH payload fields; return error Status or None."""
    if updates.get("event_type") == EventType.OFFICIAL and not request.auth.has_permission(
        PermissionKey.TAG_OFFICIAL_EVENT
    ):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={
                "endpoint": "update_event",
                "required_permission": PermissionKey.TAG_OFFICIAL_EVENT,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    effective_type = updates.get("event_type", event.event_type)
    effective_visibility = updates.get("visibility", event.visibility)
    if _is_invalid_official_visibility(effective_type, effective_visibility):
        return Status(400, ErrorOut(detail="Official events must be public."))
    effective_start = updates.get("start_datetime", event.start_datetime)
    effective_end = updates.get("end_datetime", event.end_datetime)
    effective_tbd = updates.get("datetime_tbd", event.datetime_tbd)
    dt_error = _validate_event_datetimes(
        effective_start, effective_end, effective_tbd, check_past="start_datetime" in updates
    )
    if dt_error:
        return Status(400, ErrorOut(detail=dt_error))
    return None


def _build_events_queryset(status: str, auth_user, is_authed):
    """Build the events queryset for list_events based on status and auth state."""
    if status == EventStatus.CANCELLED:
        return (
            Event.objects.prefetch_related("co_hosts", "invited_users")
            .filter(status=EventStatus.CANCELLED)
            .filter(Q(created_by=auth_user) | Q(co_hosts=auth_user))
            .distinct()
        )
    qs = Event.objects.prefetch_related("co_hosts", "invited_users").exclude(
        status=EventStatus.CANCELLED
    )
    if not is_authed:
        qs = qs.filter(Q(visibility=PageVisibility.PUBLIC) | Q(event_type=EventType.OFFICIAL))
    return qs


def _filter_invite_only(events, auth_user, status: str):
    """Remove invite-only events the user cannot see (skip for cancelled status queries)."""
    if not auth_user or status == EventStatus.CANCELLED:
        return events
    return [
        e
        for e in events
        if e.visibility != PageVisibility.INVITE_ONLY
        or _can_see_invite_only(
            auth_user,
            {str(c.id) for c in e.co_hosts.all()},
            {str(u.id) for u in e.invited_users.all()},
            e.created_by_id,
        )
    ]


@router.get("/events/", response={200: list[EventListOut], 403: ErrorOut}, auth=_optional_jwt)
def list_events(request, status: str = EventStatus.ACTIVE):
    auth_user = _authenticated_user(request.auth)
    is_authed = auth_user is not None

    if status == EventStatus.CANCELLED and not is_authed:
        return Status(403, ErrorOut(detail="Authentication required."))

    events = _filter_invite_only(
        list(_build_events_queryset(status, auth_user, is_authed)), auth_user, status
    )
    return Status(
        200,
        [
            EventListOut(
                id=str(e.id),
                title=e.title,
                description=e.description,
                start_datetime=e.start_datetime,
                end_datetime=e.end_datetime,
                location=e.location,
                latitude=float(e.latitude) if e.latitude is not None else None,
                longitude=float(e.longitude) if e.longitude is not None else None,
                event_type=e.event_type,
                visibility=e.visibility,
                photo_url=media_path(e.photo),
                whatsapp_link=_members_only(e.whatsapp_link, "", is_authed),
                partiful_link=_members_only(e.partiful_link, "", is_authed),
                other_link=_members_only(e.other_link, "", is_authed),
                price=e.price,
                venmo_link=_members_only(e.venmo_link, "", is_authed),
                cashapp_link=_members_only(e.cashapp_link, "", is_authed),
                zelle_info=_members_only(e.zelle_info, "", is_authed),
                created_by_id=str(e.created_by_id) if e.created_by_id else None,
                datetime_tbd=e.datetime_tbd,
                allow_plus_ones=e.allow_plus_ones,
                co_host_ids=[str(c.id) for c in e.co_hosts.all()],
                co_host_names=[c.display_name or c.phone_number for c in e.co_hosts.all()],
                is_past=e.is_past,
                status=e.status,
            )
            for e in events
        ],
    )


@router.get(
    "/events/{event_id}/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def get_event(request, event_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    auth_user = _authenticated_user(request.auth)
    if (
        event.visibility == PageVisibility.MEMBERS_ONLY
        and auth_user is None
        and event.event_type != EventType.OFFICIAL
    ):
        return Status(404, ErrorOut(detail="Event not found."))
    if event.visibility == PageVisibility.INVITE_ONLY:
        co_host_ids = {str(c.id) for c in event.co_hosts.all()}
        invited_user_ids = {str(u.id) for u in event.invited_users.all()}
        if not _can_see_invite_only(auth_user, co_host_ids, invited_user_ids, event.created_by_id):
            return Status(403, ErrorOut(detail="This event is invite only."))
    return Status(200, _event_out(event, request.auth))


@router.post(
    "/events/",
    response={201: EventOut, 400: ErrorOut, 403: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/d")
def create_event(request, payload: EventIn):
    # Any authenticated member can create community events.
    # Official events require tag_official_event permission.
    if payload.event_type == EventType.OFFICIAL:
        if not request.auth.has_permission(PermissionKey.TAG_OFFICIAL_EVENT):
            audit_log(
                logging.WARNING,
                "permission_denied",
                request,
                details={
                    "endpoint": "create_event",
                    "required_permission": PermissionKey.TAG_OFFICIAL_EVENT,
                },
            )
            return Status(403, ErrorOut(detail="Permission denied."))

    if _is_invalid_official_visibility(payload.event_type, payload.visibility):
        return Status(400, ErrorOut(detail="Official events must be public."))

    dt_error = _validate_event_datetimes(
        payload.start_datetime, payload.end_datetime, payload.datetime_tbd
    )
    if dt_error:
        return Status(400, ErrorOut(detail=dt_error))

    event = Event.objects.create(
        title=payload.title,
        description=payload.description,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
        whatsapp_link=payload.whatsapp_link,
        partiful_link=payload.partiful_link,
        other_link=payload.other_link,
        price=payload.price,
        venmo_link=payload.venmo_link,
        cashapp_link=payload.cashapp_link,
        zelle_info=payload.zelle_info,
        rsvp_enabled=payload.rsvp_enabled,
        datetime_tbd=payload.datetime_tbd,
        allow_plus_ones=payload.allow_plus_ones,
        event_type=payload.event_type,
        visibility=payload.visibility,
        invite_permission=payload.invite_permission,
        created_by=request.auth,
    )
    if payload.co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)
        create_cohost_added_notifications(event, payload.co_host_ids, request.auth)
    if payload.invited_user_ids:
        invited = UserModel.objects.filter(pk__in=payload.invited_user_ids)
        event.invited_users.set(invited)
        create_event_invite_notifications(event, payload.invited_user_ids, request.auth)
    audit_log(
        logging.INFO,
        "event_created",
        request,
        target_type="event",
        target_id=str(event.id),
        details={
            "title": event.title,
            "event_type": event.event_type,
            "visibility": event.visibility,
        },
    )
    return Status(201, _event_out(event, request.auth))


@router.patch(
    "/events/{event_id}/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_event(request, event_id: UUID, payload: EventPatchIn):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    if not _can_edit_event(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "update_event"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    if event.is_cancelled:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))

    updates = payload.model_dump(exclude_unset=True)
    err = _validate_update_payload(request, event, event_id, updates)
    if err:
        return err
    co_host_ids = updates.pop("co_host_ids", None)
    invited_user_ids = updates.pop("invited_user_ids", None)
    for field, value in updates.items():
        setattr(event, field, value)
    if co_host_ids is not None:
        _update_co_hosts(event, co_host_ids, request.auth)
    if invited_user_ids is not None:
        _update_invited_users(event, invited_user_ids, request.auth)

    event.save()
    audit_log(
        logging.INFO,
        "event_updated",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"fields_changed": list(updates.keys())},
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/", response={204: None, 403: ErrorOut, 404: ErrorOut}, auth=JWTAuth()
)
def delete_event(request, event_id: UUID):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "delete_event"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    event.status = EventStatus.CANCELLED
    event.save(update_fields=["status"])
    audit_log(
        logging.INFO,
        "event_cancelled",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"title": event.title},
    )
    return Status(204, None)


@router.post(
    "/events/{event_id}/photo/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="20/h")
def upload_event_photo(request, event_id: UUID, photo: UploadedFile = File(...)):  # ty: ignore[call-non-callable]
    if photo.content_type not in _ALLOWED_IMAGE_TYPES:
        return Status(400, ErrorOut(detail="File must be a JPEG, PNG, WebP, or GIF image."))
    if photo.size and photo.size > _MAX_EVENT_PHOTO_SIZE:
        return Status(400, ErrorOut(detail="Photo must be under 10 MB."))
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "upload_event_photo"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.is_cancelled:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    if event.photo:
        event.photo.delete(save=False)
    name = photo.name or ""
    ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"
    ts = int(time.time())
    event.photo.save(f"{event_id}_{ts}.{ext}", photo, save=True)
    audit_log(
        logging.INFO, "event_photo_uploaded", request, target_type="event", target_id=str(event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/photo/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_event_photo(request, event_id: UUID):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "delete_event_photo"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.is_cancelled:
        return Status(400, ErrorOut(detail="Cancelled events cannot be edited."))
    if event.photo:
        event.photo.delete(save=False)
        event.photo = ""
        event.save(update_fields=["photo"])
    audit_log(
        logging.INFO, "event_photo_deleted", request, target_type="event", target_id=str(event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.post(
    "/events/{event_id}/uncancel/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def uncancel_event(request, event_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    if not is_manager and not is_creator:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "uncancel_event"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    if not event.is_cancelled:
        return Status(400, ErrorOut(detail="Event is not cancelled."))

    event.status = EventStatus.ACTIVE
    event.save(update_fields=["status"])
    audit_log(
        logging.INFO,
        "event_uncancelled",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"title": event.title},
    )
    return Status(200, _event_out(event, request.auth))
