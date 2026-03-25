from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel

from community.models import Event, JoinRequest

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


class EventOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    location: str


class ErrorOut(BaseModel):
    detail: str


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

    return 201, JoinRequestOut(id=str(join_request.id), name=join_request.name, email=join_request.email)


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
