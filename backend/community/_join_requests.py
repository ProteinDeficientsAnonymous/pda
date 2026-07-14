import logging
from datetime import datetime, timedelta
from typing import NamedTuple
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.models import User
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._join_request_approval import (
    _provision_approved_user,
    _provision_tentative_user,
    send_join_approval,
)
from community._rsvp_counts import NON_REPORTABLE_EVENT_STATUSES
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import (
    AttendanceStatus,
    EventRSVP,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    RSVPStatus,
)

router = Router()

# Approved members stay visible in the join requests list for this many days
# after they complete onboarding, so admins can confirm someone logged in.
APPROVED_GRACE_DAYS = 3


class JoinRequestAnswerOut(BaseModel):
    question_id: str
    label: str
    answer: str


class JoinRequestOut(BaseModel):
    id: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    phone_number: str
    email: str = ""
    answers: list[JoinRequestAnswerOut] = []
    submitted_at: datetime
    status: str
    user_id: str | None = None
    previously_archived: bool = False
    approved_at: datetime | None = None
    approved_by_name: str | None = None
    rejected_at: datetime | None = None
    rejected_by_name: str | None = None
    onboarded_at: datetime | None = None
    # Prior engagement of the linked (non-member) user, so admins can gauge
    # involvement before approving. "attended" = host-marked ATTENDED;
    # "upcoming" = ATTENDING on a future event. All 0 when no user is attached.
    attended_official_count: int = 0
    attended_club_count: int = 0
    upcoming_official_count: int = 0
    upcoming_club_count: int = 0


class JoinRequestStatusIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)


class ApproveJoinRequestOut(BaseModel):
    id: str
    first_name: str = ""
    full_name: str = ""
    phone_number: str
    status: str
    magic_link_token: str | None = None
    user_id: str | None = None


BUCKETED_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)


class RsvpBreakdown(NamedTuple):
    attended_official: int = 0
    attended_club: int = 0
    upcoming_official: int = 0
    upcoming_club: int = 0


def _rsvp_bucket(rsvp: EventRSVP) -> tuple[str, str] | None:
    """(state, event_type) bucket for a linked user's rsvp, or None if it counts nowhere.

    state is "attended" (host-marked ATTENDED) or "upcoming" (ATTENDING on a
    future, time-decided event). Non-bucketed types, non-reportable events, and
    non-ATTENDING rsvps fall through to None.
    """
    event = rsvp.event
    if event.event_type not in BUCKETED_EVENT_TYPES:
        return None
    if event.status in NON_REPORTABLE_EVENT_STATUSES:
        return None
    if rsvp.status != RSVPStatus.ATTENDING:
        return None
    if rsvp.attendance == AttendanceStatus.ATTENDED:
        return ("attended", event.event_type)
    if not event.is_past and not event.datetime_tbd:
        return ("upcoming", event.event_type)
    return None


def _rsvp_breakdown(user: User | None) -> RsvpBreakdown:
    """attended (host-marked) vs upcoming ATTENDING rsvps, split by event type.

    Reads prefetched rsvps when the list endpoint supplied them, else queries
    the linked user directly.
    """
    if user is None:
        return RsvpBreakdown()
    prefetched = getattr(user, "_prefetched_objects_cache", {})
    rsvps = (
        user.event_rsvps.all()
        if "event_rsvps" in prefetched
        else EventRSVP.objects.filter(user_id=user.id).select_related("event")
    )
    counts: dict[tuple[str, str], int] = {}
    for rsvp in rsvps:
        bucket = _rsvp_bucket(rsvp)
        if bucket is not None:
            counts[bucket] = counts.get(bucket, 0) + 1
    return RsvpBreakdown(
        attended_official=counts.get(("attended", EventType.OFFICIAL), 0),
        attended_club=counts.get(("attended", EventType.CLUB), 0),
        upcoming_official=counts.get(("upcoming", EventType.OFFICIAL), 0),
        upcoming_club=counts.get(("upcoming", EventType.CLUB), 0),
    )


def _join_request_out(jr: JoinRequest) -> JoinRequestOut:
    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    phone_user = User.objects.filter(phone_number=jr.phone_number).first()
    user = jr.user or phone_user
    previously_archived = phone_user is not None and phone_user.archived_at is not None
    breakdown = _rsvp_breakdown(user)
    return JoinRequestOut(
        id=str(jr.id),
        first_name=jr.first_name,
        last_name=jr.last_name,
        full_name=jr.full_name,
        phone_number=jr.phone_number,
        email=jr.email,
        answers=answers,
        submitted_at=jr.submitted_at,
        status=jr.status,
        user_id=str(user.id) if user else None,
        previously_archived=previously_archived,
        approved_at=jr.approved_at,
        approved_by_name=jr.approved_by.full_name if jr.approved_by else None,
        rejected_at=jr.rejected_at,
        rejected_by_name=jr.rejected_by.full_name if jr.rejected_by else None,
        onboarded_at=user.onboarded_at if user else None,
        attended_official_count=breakdown.attended_official,
        attended_club_count=breakdown.attended_club,
        upcoming_official_count=breakdown.upcoming_official,
        upcoming_club_count=breakdown.upcoming_club,
    )


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=gated_jwt)
def list_join_requests(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "list_join_requests",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="list_join_requests")

    cutoff = timezone.now() - timedelta(days=APPROVED_GRACE_DAYS)
    expired_phones = User.objects.filter(
        needs_onboarding=False, onboarded_at__lt=cutoff
    ).values_list("phone_number", flat=True)
    # Legacy users onboarded before onboarded_at existed have it as null;
    # treat them as already-expired so they don't linger in the list forever.
    legacy_onboarded_phones = User.objects.filter(
        needs_onboarding=False, onboarded_at__isnull=True
    ).values_list("phone_number", flat=True)
    join_requests = (
        JoinRequest.objects.exclude(
            status=JoinRequestStatus.APPROVED,
            phone_number__in=list(expired_phones) + list(legacy_onboarded_phones),
        )
        .select_related("user", "approved_by", "rejected_by")
        .prefetch_related(
            Prefetch("user__event_rsvps", queryset=EventRSVP.objects.select_related("event"))
        )
    )
    return Status(200, [_join_request_out(jr) for jr in join_requests])


def _stamp_decision(join_request: JoinRequest, status: str, actor) -> None:
    now = timezone.now()
    join_request.status = status
    if status == JoinRequestStatus.APPROVED:
        join_request.approved_at = now
        join_request.approved_by = actor
    elif status == JoinRequestStatus.REJECTED:
        join_request.rejected_at = now
        join_request.rejected_by = actor
    join_request.save()


_DECISION_ACTIONS = {
    JoinRequestStatus.TENTATIVE: "join_request_tentative",
    JoinRequestStatus.APPROVED: "join_request_approved",
    JoinRequestStatus.REJECTED: "join_request_rejected",
}


def _apply_status_transition(
    id: UUID, status: str, actor
) -> tuple[JoinRequest, str | None, bool, bool]:
    """Stamp + provision inside one locked transaction.

    Returns ``(join_request, magic_token, user_created, promoted_from_tentative)``.
    select_for_update() serializes concurrent approvals so only one provisions.
    """
    with transaction.atomic():
        try:
            join_request = JoinRequest.objects.select_for_update().get(id=id)
        except JoinRequest.DoesNotExist:
            raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

        # TENTATIVE is not a final decision — it may still transition to
        # approved/rejected, so only the two terminal states are locked.
        if join_request.status in (JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED):
            raise_validation(Code.JoinRequest.ALREADY_DECIDED, status_code=400)

        was_tentative = join_request.status == JoinRequestStatus.TENTATIVE
        _stamp_decision(join_request, status, actor)
        if status == JoinRequestStatus.TENTATIVE:
            _provision_tentative_user(join_request, actor)
            return join_request, None, False, False
        if status == JoinRequestStatus.APPROVED:
            magic_token, user_created = _provision_approved_user(join_request, actor)
            return join_request, magic_token, user_created, was_tentative
    return join_request, None, False, False


@router.patch(
    "/join-requests/{id}/",
    response={
        200: ApproveJoinRequestOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        409: ErrorOut,
    },
    auth=gated_jwt,
)
def update_join_request_status(request, id: UUID, payload: JoinRequestStatusIn):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="join_request",
            target_id=str(id),
            details={
                "endpoint": "update_join_request_status",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="update_join_request_status")

    valid_statuses = [
        JoinRequestStatus.TENTATIVE,
        JoinRequestStatus.APPROVED,
        JoinRequestStatus.REJECTED,
    ]
    if payload.status not in valid_statuses:
        raise_validation(
            Code.JoinRequest.INVALID_STATUS,
            field="status",
            status_code=400,
            allowed=valid_statuses,
        )

    join_request, magic_token, user_created, promoted = _apply_status_transition(
        id, payload.status, request.auth
    )

    if promoted:
        send_join_approval(to=join_request.email, display_name=join_request.full_name)

    action = _DECISION_ACTIONS[payload.status]
    audit_log(
        logging.INFO,
        action,
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"full_name": join_request.full_name, "user_created": user_created},
    )

    # A promoted non-member is the linked User itself (which may have been
    # matched by email, so its phone can differ from the request's). Fall back
    # to the phone lookup for the create/reactivate paths.
    approved_user = (
        join_request.user or User.objects.filter(phone_number=join_request.phone_number).first()
    )
    return Status(
        200,
        ApproveJoinRequestOut(
            id=str(join_request.id),
            first_name=join_request.first_name,
            full_name=join_request.full_name,
            phone_number=join_request.phone_number,
            status=join_request.status,
            magic_link_token=magic_token,
            user_id=str(approved_user.id) if approved_user else None,
        ),
    )


@router.patch(
    "/join-requests/{id}/unreject/",
    response={200: JoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def unreject_join_request(request, id: UUID):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="join_request",
            target_id=str(id),
            details={
                "endpoint": "unreject_join_request",
                "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="unreject_join_request")

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

    if join_request.status != JoinRequestStatus.REJECTED:
        raise_validation(Code.JoinRequest.ONLY_REJECTED_CAN_BE_UN_REJECTED, status_code=400)

    join_request.status = JoinRequestStatus.PENDING
    join_request.save(update_fields=["status"])

    audit_log(
        logging.INFO,
        "join_request_unrejected",
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"full_name": join_request.full_name},
    )

    return Status(200, _join_request_out(join_request))
