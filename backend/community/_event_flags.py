"""Event flag submission and admin review endpoints."""

from datetime import datetime
from uuid import UUID

from config.ratelimit import rate_limit
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community.models import Event, EventFlag, EventFlagStatus

router = Router()


class EventFlagIn(BaseModel):
    reason: str = Field(max_length=FieldLimit.BIO)


class EventFlagOut(BaseModel):
    id: str
    event_id: str
    event_title: str
    flagged_by_id: str
    flagged_by_name: str
    reason: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None

    @staticmethod
    def from_model(flag: EventFlag) -> "EventFlagOut":
        flagger = flag.flagged_by
        return EventFlagOut(
            id=str(flag.id),
            event_id=str(flag.event_id),
            event_title=flag.event.title,
            flagged_by_id=str(flagger.pk),
            flagged_by_name=flagger.display_name or flagger.phone_number,
            reason=flag.reason,
            status=flag.status,
            created_at=flag.created_at,
            reviewed_at=flag.reviewed_at,
        )


class EventFlagStatusIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)


_VALID_REVIEW_STATUSES = {EventFlagStatus.DISMISSED, EventFlagStatus.ACTIONED}


@router.post(
    "/events/{event_id}/flag/",
    response={201: EventFlagOut, 400: ErrorOut, 404: ErrorOut, 409: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="3/h")
def flag_event(request, event_id: UUID, data: EventFlagIn):
    event = get_object_or_404(Event, id=event_id)

    if EventFlag.objects.filter(event=event, flagged_by=request.auth).exists():
        return Status(409, ErrorOut(detail="you already flagged this event"))

    flag = EventFlag.objects.create(
        event=event,
        flagged_by=request.auth,
        reason=data.reason,
    )

    from notifications.service import create_event_flag_notifications

    create_event_flag_notifications(event, request.auth)

    flag = EventFlag.objects.select_related("event", "flagged_by").get(pk=flag.pk)
    return Status(201, EventFlagOut.from_model(flag))


@router.get(
    "/event-flags/",
    response={200: list[EventFlagOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_event_flags(request, status: str | None = None):
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    qs = EventFlag.objects.select_related("event", "flagged_by")
    if status:
        qs = qs.filter(status=status)

    return Status(200, [EventFlagOut.from_model(f) for f in qs])


@router.patch(
    "/event-flags/{flag_id}/",
    response={200: EventFlagOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def review_event_flag(request, flag_id: UUID, data: EventFlagStatusIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    if data.status not in _VALID_REVIEW_STATUSES:
        valid = ", ".join(sorted(_VALID_REVIEW_STATUSES))
        return Status(400, ErrorOut(detail=f"Status must be one of: {valid}."))

    flag = get_object_or_404(EventFlag.objects.select_related("event", "flagged_by"), id=flag_id)
    flag.status = data.status
    flag.reviewed_at = timezone.now()
    flag.save(update_fields=["status", "reviewed_at"])

    return Status(200, EventFlagOut.from_model(flag))
