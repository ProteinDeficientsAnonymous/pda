"""Events to suggest in the message a vetter sends a tentatively-approved applicant."""

from datetime import datetime, timedelta
from uuid import UUID

from config.auth import gated_jwt
from django.db.models import QuerySet
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.permissions import PermissionKey

from community.attendance.shared import require_permission
from community.models import (
    Event,
    EventStatus,
    EventTag,
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


def chosen_options(join_request: JoinRequest) -> list[str]:
    """Lowercased answers to the join form's multi-select (checkbox) questions."""
    return [
        option.lower()
        for data in join_request.custom_answers.values()
        if isinstance(data.get("answer"), list)
        for option in data["answer"]
    ]


def club_tag_ids(options: list[str]) -> list[UUID]:
    """Tags whose name appears in a chosen option, e.g. "book club" in "book club"."""
    return [
        tag.id
        for tag in EventTag.objects.only("id", "name")
        if any(tag.name.lower() in option for option in options)
    ]


def suggest_club_event(join_request: JoinRequest, now: datetime) -> Event | None:
    tag_ids = club_tag_ids(chosen_options(join_request))
    if not tag_ids:
        return None
    return (
        _upcoming(EventType.CLUB, now + CLUB_EVENT_LEAD_TIME)
        .filter(tags__id__in=tag_ids)
        .distinct()
        .first()
    )


@router.get(
    "/join-requests/{id}/suggested-events/",
    response={200: SuggestedEventsOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def join_request_suggested_events(request, id: UUID):
    require_permission(
        request, "join_request_suggested_events", PermissionKey.APPROVE_JOIN_REQUESTS
    )
    join_request = JoinRequest.objects.filter(id=id).first()
    if join_request is None:
        raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)
    now = timezone.now()
    return Status(
        200,
        SuggestedEventsOut(
            next_official_event=_event_out(_upcoming(EventType.OFFICIAL, now).first()),
            club_event=_event_out(suggest_club_event(join_request, now)),
        ),
    )
