from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community.models import Event, JoinRequest, JoinRequestStatus

router = Router()


class JoinRequestIn(BaseModel):
    name: str
    email: str
    pronouns: str = ""
    how_they_heard: str = ""
    why_join: str


class JoinRequestOut(BaseModel):
    id: str
    name: str
    email: str
    status: str


class JoinRequestStatusIn(BaseModel):
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
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    co_host_ids: list[str] = []
    co_host_names: list[str] = []


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
    rsvp_enabled: bool | None = None
    co_host_ids: list[str] | None = None


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    if not payload.name.strip() or not payload.email.strip() or not payload.why_join.strip():
        return Status(400, ErrorOut(detail="Name, email, and why_join are required."))

    join_request = JoinRequest.objects.create(
        name=payload.name,
        email=payload.email,
        pronouns=payload.pronouns,
        how_they_heard=payload.how_they_heard,
        why_join=payload.why_join,
    )

    if settings.VETTING_EMAIL:
        send_mail(
            subject=f"New PDA Join Request: {payload.name}",
            message=(
                f"Name: {payload.name}\n"
                f"Email: {payload.email}\n"
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
            name=join_request.name,
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
                name=jr.name,
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
            name=join_request.name,
            email=join_request.email,
            status=join_request.status,
        ),
    )


def _event_out(event: Event) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    creator_name = (
        f"{creator.first_name} {creator.last_name}".strip() or creator.email if creator else None
    )
    return EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        whatsapp_link=event.whatsapp_link,
        partiful_link=event.partiful_link,
        rsvp_enabled=event.rsvp_enabled,
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=creator_name,
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[f"{u.first_name} {u.last_name}".strip() or u.email for u in co_hosts],
    )


@router.get("/events/", response={200: list[EventOut]}, auth=JWTAuth())
def list_events(request):
    events = Event.objects.select_related("created_by").prefetch_related("co_hosts").all()
    return Status(200, [_event_out(e) for e in events])


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
        rsvp_enabled=payload.rsvp_enabled,
        created_by=request.auth,
    )
    if payload.co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)
    return Status(201, _event_out(event))


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
    if payload.rsvp_enabled is not None:
        event.rsvp_enabled = payload.rsvp_enabled
    if payload.co_host_ids is not None:
        from users.models import User as UserModel

        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)

    event.save()
    return Status(200, _event_out(event))


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
