"""Events CRUD, RSVP, and event photo endpoints."""

from datetime import datetime
from uuid import UUID

from config.media_proxy import media_path
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.models import User as UserModel
from users.permissions import PermissionKey

from community._shared import ErrorOut, _authenticated_user, _members_only, _optional_jwt
from community.models import Event, EventRSVP, EventType, PageVisibility, RSVPStatus

router = Router()


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str
    phone: str | None = None
    photo_url: str = ""


class EventListOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str
    latitude: float | None = None
    longitude: float | None = None
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    price: str = ""
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    created_by_id: str | None = None
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    datetime_tbd: bool = False


class EventOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    price: str = ""
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    co_host_photo_urls: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    datetime_tbd: bool = False
    survey_slugs: list[str] = []
    invited_user_ids: list[str] = []
    invited_user_names: list[str] = []
    invited_user_photo_urls: list[str] = []


class RSVPIn(BaseModel):
    status: str


class EventIn(BaseModel):
    title: str
    description: str = ""
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str = ""
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    price: str = ""
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    rsvp_enabled: bool = False
    datetime_tbd: bool = False
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    co_host_ids: list[str] = []
    invited_user_ids: list[str] = []


class EventPatchIn(BaseModel):
    title: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str | None = None
    partiful_link: str | None = None
    other_link: str | None = None
    price: str | None = None
    venmo_link: str | None = None
    cashapp_link: str | None = None
    zelle_info: str | None = None
    rsvp_enabled: bool | None = None
    datetime_tbd: bool | None = None
    event_type: str | None = None
    visibility: str | None = None
    co_host_ids: list[str] | None = None
    invited_user_ids: list[str] | None = None


_MAX_EVENT_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}


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
            phone=r.user.phone_number if can_see_phones else None,
            photo_url=media_path(r.user.profile_photo),
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


def _can_see_invited(requesting_user, creator, co_host_ids: set[str]) -> bool:
    """Check if requesting user can see invited users list."""
    if requesting_user is None:
        return False
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    if str(requesting_user.pk) in co_host_ids:
        return True
    return requesting_user.has_permission(PermissionKey.MANAGE_EVENTS)


def _get_creator_name(creator) -> str | None:
    if creator is None:
        return None
    return creator.display_name or creator.phone_number


def _event_out(event: Event, requesting_user=None) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    auth_user = _authenticated_user(requesting_user)
    is_authed = auth_user is not None
    co_host_ids = {str(u.id) for u in co_hosts}
    phones_visible = _can_see_phones(auth_user, creator, co_host_ids)
    rsvps = list(event.rsvps.all()) if (event.rsvp_enabled and is_authed) else []
    invited = (
        list(event.invited_users.all()) if _can_see_invited(auth_user, creator, co_host_ids) else []
    )
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
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=_get_creator_name(creator),
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[u.display_name or u.phone_number for u in co_hosts],
        co_host_photo_urls=[media_path(u.profile_photo) for u in co_hosts],
        guests=_members_only(_build_guest_list(rsvps, phones_visible), [], is_authed),
        my_rsvp=_find_my_rsvp(rsvps, auth_user),
        event_type=event.event_type,
        visibility=event.visibility,
        photo_url=media_path(event.photo),
        survey_slugs=list(event.surveys.filter(is_active=True).values_list("slug", flat=True)),
        invited_user_ids=[str(u.id) for u in invited],
        invited_user_names=[u.display_name or u.phone_number for u in invited],
        invited_user_photo_urls=[media_path(u.profile_photo) for u in invited],
    )


@router.get("/events/", response={200: list[EventListOut]}, auth=_optional_jwt)
def list_events(request):
    events = Event.objects.prefetch_related("co_hosts", "invited_users").all()
    is_authed = _authenticated_user(request.auth) is not None
    if not is_authed:
        events = events.filter(visibility=PageVisibility.PUBLIC)
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
                co_host_ids=[str(c.id) for c in e.co_hosts.all()],
                co_host_names=[c.display_name or c.phone_number for c in e.co_hosts.all()],
            )
            for e in events
        ],
    )


@router.get("/events/{event_id}/", response={200: EventOut, 404: ErrorOut}, auth=_optional_jwt)
def get_event(request, event_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    if (
        event.visibility == PageVisibility.MEMBERS_ONLY
        and _authenticated_user(request.auth) is None
    ):
        return Status(404, ErrorOut(detail="Event not found."))
    return Status(200, _event_out(event, request.auth))


@router.post("/events/", response={201: EventOut, 400: ErrorOut, 403: ErrorOut}, auth=JWTAuth())
def create_event(request, payload: EventIn):
    # Any authenticated member can create community events.
    # Official events require tag_official_event permission.
    if payload.event_type == EventType.OFFICIAL:
        if not request.auth.has_permission(PermissionKey.TAG_OFFICIAL_EVENT):
            return Status(403, ErrorOut(detail="Permission denied."))

    if payload.end_datetime is not None and payload.end_datetime <= payload.start_datetime:
        return Status(400, ErrorOut(detail="end_datetime must be after start_datetime."))

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
        event_type=payload.event_type,
        visibility=payload.visibility,
        created_by=request.auth,
    )
    if payload.co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)
    if payload.invited_user_ids:
        invited = UserModel.objects.filter(pk__in=payload.invited_user_ids)
        event.invited_users.set(invited)
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

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        return Status(403, ErrorOut(detail="Permission denied."))

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("event_type") == EventType.OFFICIAL and not request.auth.has_permission(
        PermissionKey.TAG_OFFICIAL_EVENT
    ):
        return Status(403, ErrorOut(detail="Permission denied."))
    effective_start = updates.get("start_datetime", event.start_datetime)
    effective_end = updates.get("end_datetime", event.end_datetime)
    if effective_end is not None and effective_end <= effective_start:
        return Status(400, ErrorOut(detail="end_datetime must be after start_datetime."))
    co_host_ids = updates.pop("co_host_ids", None)
    invited_user_ids = updates.pop("invited_user_ids", None)
    for field, value in updates.items():
        setattr(event, field, value)
    if co_host_ids is not None:
        co_hosts = UserModel.objects.filter(pk__in=co_host_ids)
        event.co_hosts.set(co_hosts)
    if invited_user_ids is not None:
        invited = UserModel.objects.filter(pk__in=invited_user_ids)
        event.invited_users.set(invited)

    event.save()
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
        return Status(403, ErrorOut(detail="Permission denied."))

    if event.photo:
        event.photo.delete(save=False)
    event.delete()
    return Status(204, None)


@router.post(
    "/events/{event_id}/photo/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.photo:
        event.photo.delete(save=False)
    name = photo.name or ""
    ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"
    event.photo.save(f"{event_id}.{ext}", photo, save=True)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    if event.photo:
        event.photo.delete(save=False)
        event.photo = ""
        event.save(update_fields=["photo"])
    return Status(200, _event_out(event, request.auth))


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "invited_users", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    if not event.rsvp_enabled:
        return Status(400, ErrorOut(detail="RSVPs are not enabled for this event."))

    valid_statuses = RSVPStatus.values
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    EventRSVP.objects.update_or_create(
        event=event,
        user=request.auth,
        defaults={"status": payload.status},
    )
    event.refresh_from_db()
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/rsvp/",
    response={204: None, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_rsvp(request, event_id: UUID):
    deleted, _ = EventRSVP.objects.filter(event_id=event_id, user=request.auth).delete()
    if not deleted:
        return Status(404, ErrorOut(detail="RSVP not found."))
    return Status(204, None)
