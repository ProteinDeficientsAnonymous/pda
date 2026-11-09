import logging
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import NamedTuple
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.models import User
from users.permissions import PermissionKey

from community.attendance.analytics import AttendedEventOut, attended_events
from community.field_limits import FieldLimit
from community.join_requests._history import (
    PhoneLookups,
    PreviousArchiveOut,
    PreviousRejectionOut,
    phone_history,
    phone_lookups,
    previous_rejection_out,
)
from community.join_requests._rejection import Rejection, send_join_rejection, validate_rejection
from community.join_requests.approval import (
    provision_approved_user,
    provision_tentative_user,
    send_join_approval,
)
from community.join_requests.grace import WHATSAPP_GRACE_DAYS
from community.models import (
    AttendanceStatus,
    EventRSVP,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    RSVPStatus,
)
from community.rsvps.counts import NON_REPORTABLE_EVENT_STATUSES
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


class JoinRequestAnswerOut(BaseModel):
    question_id: str
    label: str
    answer: str


class JoinRequestRsvpOut(BaseModel):
    event_id: str
    title: str
    start_datetime: datetime | None = None


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
    previous_archive: PreviousArchiveOut | None = None
    # A prior request from this number was rejected — rejected applicants may
    # re-apply, so vettors need the history on the fresh request.
    previously_rejected: bool = False
    previous_rejection: PreviousRejectionOut | None = None
    status_changed_at: datetime | None = None
    status_changed_by_name: str | None = None
    approved_via_event_id: str | None = None
    approved_via_event_title: str | None = None
    rejection_reason: str = ""
    rejection_note: str = ""
    onboarded_at: datetime | None = None
    user_has_joined_whatsapp: bool = False
    # Prior engagement of the linked (non-member) user, so admins can gauge
    # involvement before approving. "attended" = host-marked ATTENDED;
    # "upcoming" = ATTENDING on a future event. All 0 when no user is attached.
    attended_official_count: int = 0
    attended_club_count: int = 0
    upcoming_official_count: int = 0
    upcoming_club_count: int = 0
    rsvp_events: list[JoinRequestRsvpOut] = []
    # all-event-types attended history for vetting
    attended_events: list[AttendedEventOut] = []


class JoinRequestStatusIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)
    rejection_reason: str = ""
    rejection_note: str = ""


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


def _is_reportable_attending(rsvp: EventRSVP) -> bool:
    """Whether an ATTENDING rsvp is for a bucketed, reportable event at all."""
    event = rsvp.event
    return (
        event.event_type in BUCKETED_EVENT_TYPES
        and event.status not in NON_REPORTABLE_EVENT_STATUSES
        and rsvp.status == RSVPStatus.ATTENDING
    )


def _rsvp_bucket(rsvp: EventRSVP) -> tuple[str, str] | None:
    """(state, event_type) bucket for a linked user's rsvp, or None if it counts nowhere.

    state is "attended" (host-marked ATTENDED) or "upcoming" (ATTENDING on a
    future, time-decided event). Non-bucketed types, non-reportable events, and
    non-ATTENDING rsvps fall through to None.
    """
    if not _is_reportable_attending(rsvp):
        return None
    event = rsvp.event
    if rsvp.attendance == AttendanceStatus.ATTENDED:
        return ("attended", event.event_type)
    if not event.is_past and not event.datetime_tbd:
        return ("upcoming", event.event_type)
    return None


def _user_event_rsvps(user: User) -> Iterable[EventRSVP]:
    """Rsvps for a user, reading the prefetched list endpoint cache when available."""
    prefetched = getattr(user, "_prefetched_objects_cache", {})
    return (
        user.event_rsvps.all()
        if "event_rsvps" in prefetched
        else EventRSVP.objects.filter(user_id=user.id).select_related("event")
    )


def _rsvp_breakdown(user: User | None) -> RsvpBreakdown:
    """attended (host-marked) vs upcoming ATTENDING rsvps, split by event type.

    Reads prefetched rsvps when the list endpoint supplied them, else queries
    the linked user directly.
    """
    if user is None:
        return RsvpBreakdown()
    counts: dict[tuple[str, str], int] = {}
    for rsvp in _user_event_rsvps(user):
        bucket = _rsvp_bucket(rsvp)
        if bucket is not None:
            counts[bucket] = counts.get(bucket, 0) + 1
    return RsvpBreakdown(
        attended_official=counts.get(("attended", EventType.OFFICIAL), 0),
        attended_club=counts.get(("attended", EventType.CLUB), 0),
        upcoming_official=counts.get(("upcoming", EventType.OFFICIAL), 0),
        upcoming_club=counts.get(("upcoming", EventType.CLUB), 0),
    )


def _rsvp_events(user: User | None) -> list[JoinRequestRsvpOut]:
    """Events (past and future) a tentative applicant has RSVP'd ATTENDING to, oldest first."""
    if user is None:
        return []
    events = [rsvp.event for rsvp in _user_event_rsvps(user) if _is_reportable_attending(rsvp)]
    events.sort(key=lambda e: (e.start_datetime is None, e.start_datetime))
    return [
        JoinRequestRsvpOut(event_id=str(e.id), title=e.title, start_datetime=e.start_datetime)
        for e in events
    ]


def _approving_event_fields(jr: JoinRequest) -> dict[str, str | None]:
    event = jr.approved_via_event
    if event is None:
        return {"approved_via_event_id": None, "approved_via_event_title": None}
    return {"approved_via_event_id": str(event.id), "approved_via_event_title": event.title}


def join_request_out(jr: JoinRequest, lookups: PhoneLookups | None = None) -> JoinRequestOut:
    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    history = phone_history(jr, lookups or phone_lookups([jr]))
    user = jr.user or history.phone_user
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
        previously_archived=history.previous_archive is not None,
        previous_archive=history.previous_archive,
        previously_rejected=history.previous_rejection is not None,
        previous_rejection=previous_rejection_out(history.previous_rejection),
        status_changed_at=jr.status_changed_at,
        status_changed_by_name=jr.status_changed_by.full_name if jr.status_changed_by else None,
        **_approving_event_fields(jr),
        rejection_reason=jr.rejection_reason,
        rejection_note=jr.rejection_note,
        onboarded_at=user.onboarded_at if user else None,
        user_has_joined_whatsapp=user.has_joined_whatsapp if user else False,
        attended_official_count=breakdown.attended_official,
        attended_club_count=breakdown.attended_club,
        upcoming_official_count=breakdown.upcoming_official,
        upcoming_club_count=breakdown.upcoming_club,
        rsvp_events=_rsvp_events(user),
        # Only attribute per-event attendance history to a confidently-linked
        # account. A bare phone match could be a different guest (Issue 1107).
        attended_events=attended_events(_user_event_rsvps(jr.user)) if jr.user else [],
    )


_ADMITTED_STATUSES = (JoinRequestStatus.APPROVED, JoinRequestStatus.TENTATIVE)


def _superseded_by_pause(jr: JoinRequest, lookups: PhoneLookups) -> bool:
    """A pause clears has_joined_whatsapp, so rows decided before it would otherwise reappear."""
    user = lookups.users_by_phone.get(jr.phone_number)
    if user is None or jr.status not in _ADMITTED_STATUSES:
        return False
    decided_at = jr.status_changed_at or jr.submitted_at
    stamps = (user.attendance_paused_at, user.restored_at)
    return any(stamp is not None and stamp > decided_at for stamp in stamps)


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=gated_jwt)
def list_join_requests(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                details={
                    "endpoint": "list_join_requests",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                }
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="list_join_requests")

    cutoff = timezone.now() - timedelta(days=WHATSAPP_GRACE_DAYS)
    # Legacy users onboarded before onboarded_at existed have it as null;
    # treat them as past the grace window.
    expired_phones = User.objects.filter(
        Q(onboarded_at__lt=cutoff) | Q(onboarded_at__isnull=True),
        needs_onboarding=False,
        has_joined_whatsapp=True,
    ).values_list("phone_number", flat=True)
    join_requests = (
        JoinRequest.objects.exclude(
            status__in=_ADMITTED_STATUSES,
            phone_number__in=expired_phones,
        )
        .select_related("user", "status_changed_by", "approved_via_event")
        .prefetch_related(
            Prefetch("user__event_rsvps", queryset=EventRSVP.objects.select_related("event"))
        )
    )
    join_requests = list(join_requests)
    lookups = phone_lookups(join_requests)
    rows = [jr for jr in join_requests if not _superseded_by_pause(jr, lookups)]
    return Status(200, [join_request_out(jr, lookups) for jr in rows])


def _stamp_decision(join_request: JoinRequest, status: str, actor, rejection: Rejection) -> None:
    join_request.status = status
    join_request.status_changed_at = timezone.now()
    join_request.status_changed_by = actor
    if status == JoinRequestStatus.REJECTED:
        join_request.rejection_reason, join_request.rejection_note = rejection
    join_request.save()


_DECISION_ACTIONS = {
    JoinRequestStatus.TENTATIVE: "join_request_tentative",
    JoinRequestStatus.APPROVED: "join_request_approved",
    JoinRequestStatus.REJECTED: "join_request_rejected",
}


def _apply_status_transition(
    id: UUID, status: str, actor, rejection: Rejection
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

        if join_request.status in (JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED):
            raise_validation(Code.JoinRequest.ALREADY_DECIDED, status_code=400)
        was_tentative = join_request.status == JoinRequestStatus.TENTATIVE
        # A tentative person who shouldn't stay is archived or guidelines-paused instead.
        if was_tentative and status == JoinRequestStatus.REJECTED:
            raise_validation(Code.JoinRequest.TENTATIVE_CANNOT_BE_REJECTED, status_code=400)

        _stamp_decision(join_request, status, actor, rejection)
        if status == JoinRequestStatus.TENTATIVE:
            _, magic_token = provision_tentative_user(join_request, actor)
            return join_request, magic_token, False, False
        if status == JoinRequestStatus.APPROVED:
            magic_token, user_created = provision_approved_user(
                join_request, actor, was_tentative=was_tentative
            )
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
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.JOIN_REQUEST,
                id=str(id),
                details={
                    "endpoint": "update_join_request_status",
                    "required_permission": PermissionKey.APPROVE_JOIN_REQUESTS,
                },
            ),
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

    rejection = (
        validate_rejection(payload.rejection_reason, payload.rejection_note)
        if payload.status == JoinRequestStatus.REJECTED
        else Rejection()
    )
    join_request, magic_token, user_created, promoted = _apply_status_transition(
        id, payload.status, request.auth, rejection
    )

    if promoted:
        send_join_approval(
            to=join_request.email,
            display_name=join_request.full_name,
            first_name=join_request.first_name,
        )
    if payload.status == JoinRequestStatus.REJECTED:
        send_join_rejection(join_request)

    action = _DECISION_ACTIONS[payload.status]
    audit_log(
        logging.INFO,
        action,
        request,
        target=AuditTarget(
            type=AuditTargetType.JOIN_REQUEST,
            id=str(join_request.id),
            details={
                "full_name": join_request.full_name,
                "user_created": user_created,
                "rejection_reason": join_request.rejection_reason,
            },
        ),
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
