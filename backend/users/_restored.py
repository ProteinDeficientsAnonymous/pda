import logging
from datetime import datetime, timedelta

from community.attendance.analytics import AttendedEventOut, qualifying_attendance_q
from community.join_requests.grace import WHATSAPP_GRACE_DAYS
from community.models import EventRSVP
from community.validation import Code, raise_validation
from config.audit import AuditTarget, audit_log
from config.auth import gated_jwt
from django.db.models import Prefetch, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from users.models import User
from users.permissions import PermissionKey
from users.schemas import ErrorOut

router = Router()

RECENT_EVENT_COUNT = 2


class RestoredMemberOut(BaseModel):
    id: str
    full_name: str
    phone_number: str
    restored_at: datetime
    has_joined_whatsapp: bool
    recent_events: list[AttendedEventOut]


@router.get(
    "/users/restored/", response={200: list[RestoredMemberOut], 403: ErrorOut}, auth=gated_jwt
)
def list_restored_members(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        details = {
            "endpoint": "list_restored_members",
            "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
        }
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(details=details),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="list_restored_members")

    cutoff = timezone.now() - timedelta(days=WHATSAPP_GRACE_DAYS)
    qualifying = (
        EventRSVP.objects.filter(qualifying_attendance_q())
        .select_related("event")
        .only("user", "event__title", "event__start_datetime", "event__event_type")
        .order_by("-event__start_datetime", "event_id")
    )
    users = (
        User.objects.active_members()
        .filter(restored_at__isnull=False)
        .exclude(Q(restored_at__lt=cutoff) & Q(has_joined_whatsapp=True))
        .order_by("-restored_at", "id")
        .prefetch_related(Prefetch("event_rsvps", queryset=qualifying, to_attr="qualifying_rsvps"))
    )
    return Status(
        200,
        [
            RestoredMemberOut(
                id=str(u.id),
                full_name=u.full_name,
                phone_number=u.phone_number,
                restored_at=u.restored_at,
                has_joined_whatsapp=u.has_joined_whatsapp,
                recent_events=[
                    AttendedEventOut.from_rsvp(r) for r in u.qualifying_rsvps[:RECENT_EVENT_COUNT]
                ],
            )
            for u in users
        ],
    )
