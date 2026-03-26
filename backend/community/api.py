import re
from datetime import datetime
from uuid import UUID

import phonenumbers
from django.conf import settings
from django.core.mail import send_mail
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community.models import (
    CommunityGuidelines,
    Event,
    EventRSVP,
    JoinRequest,
    JoinRequestStatus,
    RSVPStatus,
)

router = Router()


class GuidelinesOut(BaseModel):
    content: str
    updated_at: datetime


class GuidelinesPatchIn(BaseModel):
    content: str


class JoinRequestIn(BaseModel):
    display_name: str
    phone_number: str
    email: str = ""
    pronouns: str = ""
    how_they_heard: str = ""
    why_join: str


class JoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    email: str
    status: str


class JoinRequestStatusIn(BaseModel):
    status: str


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str


class EventOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    location: str
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None


class RSVPIn(BaseModel):
    status: str


class ErrorOut(BaseModel):
    detail: str


class EventIn(BaseModel):
    title: str
    description: str = ""
    start_datetime: datetime
    end_datetime: datetime
    location: str = ""
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    rsvp_enabled: bool = False
    co_host_ids: list[str] = []


class EventPatchIn(BaseModel):
    title: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    whatsapp_link: str | None = None
    partiful_link: str | None = None
    other_link: str | None = None
    rsvp_enabled: bool | None = None
    co_host_ids: list[str] | None = None


DISPLAY_NAME_RE = re.compile(r"^[a-zA-Z ]+$")


def _validate_phone(raw: str) -> str:
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.phonenumberutil.NumberParseException as e:
        raise ValueError(str(e)) from e
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@router.get("/guidelines/", response={200: GuidelinesOut}, auth=JWTAuth())
def get_guidelines(request):
    g = CommunityGuidelines.get()
    return Status(200, GuidelinesOut(content=g.content, updated_at=g.updated_at))


@router.patch("/guidelines/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_guidelines(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_GUIDELINES):
        return Status(403, ErrorOut(detail="Permission denied."))
    g = CommunityGuidelines.get()
    g.content = payload.content
    g.save()
    return Status(200, GuidelinesOut(content=g.content, updated_at=g.updated_at))


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()
    if not display_name or not payload.why_join.strip():
        return Status(400, ErrorOut(detail="display_name and why_join are required."))
    if not DISPLAY_NAME_RE.match(display_name) or len(display_name) > 64:
        return Status(
            400,
            ErrorOut(detail="Display name must contain only letters and spaces (max 64 chars)."),
        )

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    join_request = JoinRequest.objects.create(
        display_name=display_name,
        phone_number=validated_phone,
        email=payload.email,
        pronouns=payload.pronouns,
        how_they_heard=payload.how_they_heard,
        why_join=payload.why_join,
    )

    if settings.VETTING_EMAIL:
        send_mail(
            subject=f"New PDA Join Request: {display_name}",
            message=(
                f"Display Name: {display_name}\n"
                f"Phone: {validated_phone}\n"
                f"Email: {payload.email or '(not provided)'}\n"
                f"Pronouns: {payload.pronouns}\n"
                f"How they heard: {payload.how_they_heard}\n\n"
                f"Why they want to join:\n{payload.why_join}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
            fail_silently=True,
        )

    return Status(
        201,
        JoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            email=join_request.email,
            status=join_request.status,
        ),
    )


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=JWTAuth())
def list_join_requests(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    join_requests = JoinRequest.objects.all()
    return Status(
        200,
        [
            JoinRequestOut(
                id=str(jr.id),
                display_name=jr.display_name,
                phone_number=jr.phone_number,
                email=jr.email,
                status=jr.status,
            )
            for jr in join_requests
        ],
    )


@router.patch(
    "/join-requests/{id}/",
    response={200: JoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_request_status(request, id: UUID, payload: JoinRequestStatusIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    valid_statuses = [JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED]
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        return Status(404, ErrorOut(detail="Join request not found."))

    join_request.status = payload.status
    join_request.save()

    return Status(
        200,
        JoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            email=join_request.email,
            status=join_request.status,
        ),
    )


def _event_out(event: Event, requesting_user=None) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    creator_name = creator.display_name or creator.phone_number if creator else None
    rsvps = list(event.rsvps.select_related("user").all()) if event.rsvp_enabled else []
    guests = [
        RSVPGuestOut(
            user_id=str(r.user_id),
            name=r.user.display_name or r.user.phone_number,
            status=r.status,
        )
        for r in rsvps
    ]
    my_rsvp = None
    if requesting_user is not None:
        for r in rsvps:
            if r.user_id == requesting_user.pk:
                my_rsvp = r.status
                break
    return EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        whatsapp_link=event.whatsapp_link,
        partiful_link=event.partiful_link,
        other_link=event.other_link,
        rsvp_enabled=event.rsvp_enabled,
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=creator_name,
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[u.display_name or u.phone_number for u in co_hosts],
        guests=guests,
        my_rsvp=my_rsvp,
    )


@router.get("/events/", response={200: list[EventOut]}, auth=JWTAuth())
def list_events(request):
    events = (
        Event.objects.select_related("created_by").prefetch_related("co_hosts", "rsvps__user").all()
    )
    return Status(200, [_event_out(e, request.auth) for e in events])


@router.post("/events/", response={201: EventOut, 403: ErrorOut}, auth=JWTAuth())
def create_event(request, payload: EventIn):
    from users.models import User as UserModel

    event = Event.objects.create(
        title=payload.title,
        description=payload.description,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        location=payload.location,
        whatsapp_link=payload.whatsapp_link,
        partiful_link=payload.partiful_link,
        other_link=payload.other_link,
        rsvp_enabled=payload.rsvp_enabled,
        created_by=request.auth,
    )
    if payload.co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)
    return Status(201, _event_out(event, request.auth))


@router.patch(
    "/events/{event_id}/", response={200: EventOut, 403: ErrorOut, 404: ErrorOut}, auth=JWTAuth()
)
def update_event(request, event_id: UUID, payload: EventPatchIn):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    if not is_manager and not is_creator:
        return Status(403, ErrorOut(detail="Permission denied."))

    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.start_datetime is not None:
        event.start_datetime = payload.start_datetime
    if payload.end_datetime is not None:
        event.end_datetime = payload.end_datetime
    if payload.location is not None:
        event.location = payload.location
    if payload.whatsapp_link is not None:
        event.whatsapp_link = payload.whatsapp_link
    if payload.partiful_link is not None:
        event.partiful_link = payload.partiful_link
    if payload.other_link is not None:
        event.other_link = payload.other_link
    if payload.rsvp_enabled is not None:
        event.rsvp_enabled = payload.rsvp_enabled
    if payload.co_host_ids is not None:
        from users.models import User as UserModel

        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)

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
    if not is_manager and not is_creator:
        return Status(403, ErrorOut(detail="Permission denied."))

    event.delete()
    return Status(204, None)


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "rsvps__user")
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
        .prefetch_related("co_hosts", "rsvps__user")
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
