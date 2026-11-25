"""Events to suggest in the message a vetter sends a tentatively-approved applicant."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db.models import QuerySet
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.permissions import PermissionKey

from community.models import (
    Event,
    EventStatus,
    EventType,
    JoinRequest,
    PageVisibility,
)
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()

# Gives a new applicant time to sign in and plan before the club event.
CLUB_EVENT_LEAD_TIME = timedelta(days=7)


class SuggestedEventOut(BaseModel):
    id: str
    slug: str
    title: str
    start_datetime: datetime


class SuggestedEventsOut(BaseModel):
    next_official_event: SuggestedEventOut | None
    club_event: SuggestedEventOut | None


def _event_out(event: Event | None) -> SuggestedEventOut | None:
    if event is None or event.start_datetime is None:
        return None
    return SuggestedEventOut(
        id=str(event.id),
        slug=event.slug,
        title=event.title,
        start_datetime=event.start_datetime,
    )


def _upcoming(event_type: str, starts_after: datetime) -> QuerySet[Event]:
    return (
        Event.objects.filter(
            event_type=event_type,
            status=EventStatus.ACTIVE,
            datetime_tbd=False,
            start_datetime__gte=starts_after,
        )
        .exclude(visibility=PageVisibility.INVITE_ONLY)
        .order_by("start_datetime")
    )


def suggest_club_event(join_request: JoinRequest, now: datetime) -> Event | None:
    return (
        _upcoming(EventType.CLUB, now + CLUB_EVENT_LEAD_TIME)
        .filter(club__in=join_request.interested_clubs.all())
        .first()
    )


@router.get(
    "/join-requests/{id}/suggested-events/",
    response={200: SuggestedEventsOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def join_request_suggested_events(request, id: UUID):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.JOIN_REQUEST,
                id=str(id),
                details={
                    "endpoint": "join_request_suggested_events",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                },
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="join_request_suggested_events")
    join_request = JoinRequest.objects.filter(id=id).first()
    if join_request is None:
        raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)
    now = timezone.now()
    return Status(
        200,
        SuggestedEventsOut(
            next_official_event=_event_out(
                _upcoming(EventType.OFFICIAL, now).filter(rsvp_enabled=True).first()
            ),
            club_event=_event_out(suggest_club_event(join_request, now)),
        ),
    )
