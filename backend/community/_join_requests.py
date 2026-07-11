import logging
from datetime import datetime, timedelta
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field
from users.models import User
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._join_request_approval import _provision_approved_user
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import (
    EventRSVP,
    EventType,
    JoinRequest,
    JoinRequestStatus,
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
    display_name: str
    phone_number: str
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
    # RSVPs the linked (non-member) user holds on official events. Lets admins
    # see prior engagement before approving; 0 when no user is attached.
    attached_user_official_rsvp_count: int = 0


class JoinRequestStatusIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)


class ApproveJoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    status: str
    magic_link_token: str | None = None
    user_id: str | None = None


def _official_rsvp_count(jr: JoinRequest) -> int:
    # The list endpoint annotates this to avoid an N+1; single-row callers have
    # no annotation and fall back to a direct count.
    annotated = getattr(jr, "official_rsvp_count", None)
    if annotated is not None:
        return annotated
    if not jr.user_id:
        return 0
    return EventRSVP.objects.filter(
        user_id=jr.user_id, event__event_type=EventType.OFFICIAL
    ).count()


def _join_request_out(jr: JoinRequest) -> JoinRequestOut:
    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    phone_user = User.objects.filter(phone_number=jr.phone_number).first()
    user = jr.user or phone_user
    previously_archived = phone_user is not None and phone_user.archived_at is not None
    official_rsvp_count = _official_rsvp_count(jr)
    return JoinRequestOut(
        id=str(jr.id),
        display_name=jr.display_name,
        phone_number=jr.phone_number,
        answers=answers,
        submitted_at=jr.submitted_at,
        status=jr.status,
        user_id=str(user.id) if user else None,
        previously_archived=previously_archived,
        approved_at=jr.approved_at,
        approved_by_name=jr.approved_by.display_name if jr.approved_by else None,
        rejected_at=jr.rejected_at,
        rejected_by_name=jr.rejected_by.display_name if jr.rejected_by else None,
        onboarded_at=user.onboarded_at if user else None,
        attached_user_official_rsvp_count=official_rsvp_count,
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
        .annotate(
            official_rsvp_count=Count(
                "user__event_rsvps",
                filter=Q(user__event_rsvps__event__event_type=EventType.OFFICIAL),
            )
        )
    )
    return Status(200, [_join_request_out(jr) for jr in join_requests])


def _stamp_decision(join_request: JoinRequest, status: str, actor) -> None:
    now = timezone.now()
    join_request.status = status
    if status == JoinRequestStatus.APPROVED:
        join_request.approved_at = now
        join_request.approved_by = actor
    else:
        join_request.rejected_at = now
        join_request.rejected_by = actor
    join_request.save()


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

    valid_statuses = [JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED]
    if payload.status not in valid_statuses:
        raise_validation(
            Code.JoinRequest.INVALID_STATUS,
            field="status",
            status_code=400,
            allowed=valid_statuses,
        )

    # select_for_update() serializes concurrent approvals: the second blocks until
    # the first commits, then sees APPROVED and gets ALREADY_DECIDED. Provisioning
    # shares the transaction so a mid-provision failure never leaves the request
    # APPROVED with a half-promoted user.
    magic_token = None
    user_created = False
    with transaction.atomic():
        try:
            join_request = JoinRequest.objects.select_for_update().get(id=id)
        except JoinRequest.DoesNotExist:
            raise_validation(Code.JoinRequest.NOT_FOUND, status_code=404)

        if join_request.status in (JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED):
            raise_validation(Code.JoinRequest.ALREADY_DECIDED, status_code=400)

        _stamp_decision(join_request, payload.status, request.auth)
        if payload.status == JoinRequestStatus.APPROVED:
            magic_token, user_created = _provision_approved_user(join_request, request.auth)

    action = (
        "join_request_approved"
        if payload.status == JoinRequestStatus.APPROVED
        else "join_request_rejected"
    )
    audit_log(
        logging.INFO,
        action,
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"display_name": join_request.display_name, "user_created": user_created},
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
            display_name=join_request.display_name,
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
        details={"display_name": join_request.display_name},
    )

    return Status(200, _join_request_out(join_request))
