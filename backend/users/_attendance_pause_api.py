from datetime import datetime
from enum import StrEnum
from uuid import UUID

from community.validation import Code, raise_validation
from config.auth import gated_jwt
from ninja.responses import Status
from pydantic import BaseModel

from users._attendance_pause import PauseImpact, pause_impact
from users._management import require_manage_users
from users._management import router as management_router
from users.models import MembershipStatus, User
from users.schemas import ErrorOut

router = management_router


class PauseRole(StrEnum):
    RSVP = "rsvp"
    HOSTING = "hosting"


class PauseOutcome(StrEnum):
    KEPT = "kept"
    REMOVED = "removed"
    DRAFTED = "drafted"


_BUCKETS = {
    "kept_rsvps": (PauseRole.RSVP, PauseOutcome.KEPT),
    "removed_rsvps": (PauseRole.RSVP, PauseOutcome.REMOVED),
    "removed_hosting": (PauseRole.HOSTING, PauseOutcome.REMOVED),
    "drafted_events": (PauseRole.HOSTING, PauseOutcome.DRAFTED),
}


class PauseImpactEventOut(BaseModel):
    id: str
    title: str
    start_datetime: datetime | None
    role: PauseRole
    outcome: PauseOutcome


class PausePreviewOut(BaseModel):
    events: list[PauseImpactEventOut]


def _preview_events(impact: PauseImpact) -> list[PauseImpactEventOut]:
    return [
        PauseImpactEventOut(
            id=str(event.pk),
            title=event.title,
            start_datetime=event.start_datetime,
            role=role,
            outcome=outcome,
        )
        for bucket, (role, outcome) in _BUCKETS.items()
        for event in getattr(impact, bucket)
    ]


@router.get(
    "/users/{user_id}/attendance-pause-preview/",
    response={200: PausePreviewOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def attendance_pause_preview(request, user_id: UUID):
    return _pause_preview(request, user_id, MembershipStatus.ATTENDANCE_PAUSED)


@router.get(
    "/users/{user_id}/guidelines-pause-preview/",
    response={200: PausePreviewOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def guidelines_pause_preview(request, user_id: UUID):
    return _pause_preview(request, user_id, MembershipStatus.GUIDELINES_PAUSED)


def _pause_preview(request, user_id: UUID, pause: MembershipStatus):
    require_manage_users(request, f"{pause}_preview", str(user_id))
    try:
        user = User.objects.members_or_archived().get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    impact = pause_impact(user, pause)
    return Status(200, PausePreviewOut(events=_preview_events(impact)))
