import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.core.exceptions import ValidationError
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from users.models import User
from users.permissions import PermissionKey

from community._attendance_mark_schemas import AttendanceMarkIn, AttendanceMarkOut
from community._attendance_shared import require_permission
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import (
    AttendanceStatus,
    Event,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)

router = Router()

_MARKABLE_EVENT_TYPES = {EventType.OFFICIAL, EventType.CLUB, EventType.COMMUNITY}


def _resolve_event(payload: AttendanceMarkIn, request) -> Event:
    if payload.event_id:
        try:
            return Event.objects.get(id=payload.event_id)
        except (Event.DoesNotExist, ValidationError, ValueError):
            raise_validation(Code.Event.NOT_FOUND, status_code=404)

    if not payload.event_title or not payload.event_date:
        raise_validation(Code.AttendanceMark.EVENT_OR_TITLE_REQUIRED, status_code=400)

    event_type = payload.event_type or EventType.COMMUNITY
    if event_type not in _MARKABLE_EVENT_TYPES:
        raise_validation(Code.AttendanceMark.INVALID_EVENT_TYPE, status_code=400)

    start = timezone.make_aware(
        timezone.datetime.combine(payload.event_date, timezone.datetime.min.time())
    )
    return Event.objects.create(
        title=payload.event_title,
        start_datetime=start,
        event_type=event_type,
        visibility=PageVisibility.MEMBERS_ONLY,
        status=EventStatus.ACTIVE,
        rsvp_enabled=False,
        is_legacy=True,
        created_by=request.auth,
    )


@router.post(
    "/events/attendance-mark/",
    response={
        200: AttendanceMarkOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        429: ErrorOut,
    },
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="20/h")
def mark_attendance(request, payload: AttendanceMarkIn):
    require_permission(request, "mark_attendance", PermissionKey.MANAGE_USERS)

    user_ids = list(dict.fromkeys(payload.user_ids))
    if not user_ids:
        raise_validation(Code.AttendanceMark.NO_MEMBERS_SELECTED, status_code=400)

    event = _resolve_event(payload, request)
    users_by_id = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}

    created_count = updated_count = 0
    for user_id in user_ids:
        user = users_by_id.get(user_id)
        if user is None:
            continue
        _, created = event.rsvps.update_or_create(
            user=user,
            defaults={
                "status": RSVPStatus.ATTENDING,
                "attendance": AttendanceStatus.ATTENDED,
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1
    skipped_count = len(user_ids) - len(users_by_id)

    audit_log(
        logging.INFO,
        "attendance_marked",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event.id),
            details={
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
            },
        ),
    )
    return Status(
        200,
        AttendanceMarkOut(
            event_id=str(event.id),
            event_title=event.title,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
        ),
    )
