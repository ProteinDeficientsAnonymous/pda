import logging
from datetime import datetime, timedelta
from enum import StrEnum

from community.attendance.analytics import AttendedEventOut, qualifying_attendance_q
from community.join_requests.grace import WHATSAPP_GRACE_DAYS
from community.models import EventRSVP
from community.validation import Code, raise_validation
from config.audit import AuditTarget, audit_log
from config.auth import gated_jwt
from django.db.models import OuterRef, Prefetch, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from users.member_search import qualifying_rsvps
from users.models import User
from users.permissions import PermissionKey
from users.schemas import ErrorOut

router = Router()

RECENT_EVENT_COUNT = 2


class ReturnKind(StrEnum):
    RESTORED = "restored"
    UNPAUSED = "unpaused"


class RestoredMemberOut(BaseModel):
    id: str
    full_name: str
    phone_number: str
    kind: ReturnKind
    restored_at: datetime | None
    unpaused_at: datetime | None
    came_in_person_at: datetime | None
    has_joined_whatsapp: bool
    recent_events: list[AttendedEventOut]

    @classmethod
    def from_user(cls, u: User) -> "RestoredMemberOut":
        return cls(
            id=str(u.id),
            full_name=u.full_name,
            phone_number=u.phone_number,
            kind=ReturnKind.UNPAUSED if u.unpaused_at else ReturnKind.RESTORED,
            restored_at=u.restored_at,
            unpaused_at=u.unpaused_at,
            came_in_person_at=u.came_in_person_at,
            has_joined_whatsapp=u.has_joined_whatsapp,
            recent_events=[
                AttendedEventOut.from_rsvp(r) for r in u.qualifying_rsvps[:RECENT_EVENT_COUNT]
            ],
        )


def _listed_members() -> QuerySet[User]:
    """Restored or unpaused members, until WHATSAPP_GRACE_DAYS after their return once they've joined the whatsapp."""
    cutoff = timezone.now() - timedelta(days=WHATSAPP_GRACE_DAYS)
    # An unpause comes after any earlier restore (a pause in between clears unpaused_at), so it wins.
    first_back = (
        qualifying_rsvps()
        .filter(event__start_datetime__gte=OuterRef("unpaused_at"))
        .order_by("event__start_datetime")
        .values("event__start_datetime")[:1]
    )
    kept = (
        Q(has_joined_whatsapp=False)
        | Q(unpaused_at__isnull=True, restored_at__gte=cutoff)
        | Q(unpaused_at__isnull=False, came_in_person_at__isnull=True)
        | Q(came_in_person_at__gte=cutoff)
    )
    return (
        User.objects.active_members()
        .filter(Q(restored_at__isnull=False) | Q(unpaused_at__isnull=False))
        .annotate(came_in_person_at=Subquery(first_back))
        .filter(kept)
        .order_by(Coalesce("unpaused_at", "restored_at").desc(), "id")
    )


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

    qualifying = (
        EventRSVP.objects.filter(qualifying_attendance_q())
        .select_related("event")
        .only("user", "event__title", "event__start_datetime", "event__event_type")
        .order_by("-event__start_datetime", "event_id")
    )
    users = _listed_members().prefetch_related(
        Prefetch("event_rsvps", queryset=qualifying, to_attr="qualifying_rsvps")
    )
    return Status(200, [RestoredMemberOut.from_user(u) for u in users])
