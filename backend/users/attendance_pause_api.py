import logging
from datetime import datetime
from enum import StrEnum

from community.validation import Code, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja.responses import Status
from pydantic import BaseModel

from users._attendance_pause import (
    MEMBER_OR_ATTENDANCE_PAUSED_Q,
    PauseImpact,
    attendance_pause_impact,
)
from users._management import router as management_router
from users.models import User
from users.permissions import PermissionKey
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
    "kept_hosting": (PauseRole.HOSTING, PauseOutcome.KEPT),
    "removed_hosting": (PauseRole.HOSTING, PauseOutcome.REMOVED),
    "drafted_events": (PauseRole.HOSTING, PauseOutcome.DRAFTED),
}


class PauseImpactEventOut(BaseModel):
    id: str
    title: str
    start_datetime: datetime | None
    role: PauseRole
    outcome: PauseOutcome


class AttendancePausePreviewOut(BaseModel):
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
    response={200: AttendancePausePreviewOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def attendance_pause_preview(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.USER,
                id=user_id,
                details={
                    "endpoint": "attendance_pause_preview",
                    "required_permission": PermissionKey.MANAGE_USERS,
                },
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="attendance_pause_preview")
    try:
        user = User.objects.filter(MEMBER_OR_ATTENDANCE_PAUSED_Q).get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    events = _preview_events(attendance_pause_impact(user))
    return Status(200, AttendancePausePreviewOut(events=events))
