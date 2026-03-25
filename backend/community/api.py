from datetime import datetime
from typing import Optional
from uuid import UUID

from django.conf import settings
from django.core.mail import send_mail
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel

from community.models import Event, JoinRequest, JoinRequestStatus
from users.permissions import PermissionKey

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


class ErrorOut(BaseModel):
    detail: str


class EventIn(BaseModel):
    title: str
    description: str = ""
    start_datetime: datetime
    end_datetime: datetime
    location: str = ""


class EventPatchIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    if not payload.name.strip() or not payload.email.strip() or not payload.why_join.strip():
        return 400, ErrorOut(detail="Name, email, and why_join are required.")

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

    return 201, JoinRequestOut(
        id=str(join_request.id),
        name=join_request.name,
        email=join_request.email,
        status=join_request.status,
    )


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=JWTAuth())
def list_join_requests(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return 403, ErrorOut(detail="Permission denied.")

    join_requests = JoinRequest.objects.all()
    return 200, [
        JoinRequestOut(
            id=str(jr.id),
            name=jr.name,
            email=jr.email,
            status=jr.status,
        )
        for jr in join_requests
    ]


@router.patch(
    "/join-requests/{id}/",
    response={200: JoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_request_status(request, id: UUID, payload: JoinRequestStatusIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return 403, ErrorOut(detail="Permission denied.")

    valid_statuses = [JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED]
    if payload.status not in valid_statuses:
        return 400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}.")

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        return 404, ErrorOut(detail="Join request not found.")

    join_request.status = payload.status
    join_request.save()

    return 200, JoinRequestOut(
        id=str(join_request.id),
        name=join_request.name,
        email=join_request.email,
        status=join_request.status,
    )


@router.get("/events/", response={200: list[EventOut]}, auth=JWTAuth())
def list_events(request):
    events = Event.objects.all()
    return 200, [
        EventOut(
            id=str(e.id),
            title=e.title,
            description=e.description,
            start_datetime=e.start_datetime,
            end_datetime=e.end_datetime,
            location=e.location,
        )
        for e in events
    ]


@router.post("/events/", response={201: EventOut, 403: ErrorOut}, auth=JWTAuth())
def create_event(request, payload: EventIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return 403, ErrorOut(detail="Permission denied.")

    event = Event.objects.create(
        title=payload.title,
        description=payload.description,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        location=payload.location,
    )
    return 201, EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
    )


@router.patch("/events/{event_id}/", response={200: EventOut, 403: ErrorOut, 404: ErrorOut}, auth=JWTAuth())
def update_event(request, event_id: UUID, payload: EventPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return 403, ErrorOut(detail="Permission denied.")

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return 404, ErrorOut(detail="Event not found.")

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

    event.save()
    return 200, EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
    )


@router.delete("/events/{event_id}/", response={204: None, 403: ErrorOut, 404: ErrorOut}, auth=JWTAuth())
def delete_event(request, event_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return 403, ErrorOut(detail="Permission denied.")

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return 404, ErrorOut(detail="Event not found.")

    event.delete()
    return 204, None
