"""Join request submission, management, and check-phone endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from config.audit import audit_log
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.service import create_join_request_notifications
from pydantic import BaseModel, Field, field_validator
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut, _validate_phone, logger, validate_display_name
from community.models import (
    JoinFormQuestion,
    JoinFormQuestionType,
    JoinRequest,
    JoinRequestStatus,
)

router = Router()


class JoinRequestIn(BaseModel):
    display_name: str = Field(max_length=FieldLimit.DISPLAY_NAME)
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    answers: dict[str, str] = {}
    # Honeypot: hidden field human users never fill in. Bots auto-complete
    # every input, so a non-empty value is a strong spam signal.
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(cls, v: dict[str, str]) -> dict[str, str]:
        for key, answer in v.items():
            if len(answer) > FieldLimit.DESCRIPTION:
                raise ValueError(
                    f"Answer for question {key} exceeds {FieldLimit.DESCRIPTION} characters."
                )
        return v


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


class JoinRequestStatusIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)


class ApproveJoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    status: str
    magic_link_token: str | None = None
    user_id: str | None = None


class CheckPhoneOut(BaseModel):
    status: str  # "member" | "pending" | "unknown"


class CheckPhoneIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


def _join_request_out(jr: JoinRequest) -> JoinRequestOut:
    from users.models import User

    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    user = User.objects.filter(phone_number=jr.phone_number).first()
    previously_archived = bool(
        User.objects.filter(phone_number=jr.phone_number, archived_at__isnull=False).exists()
    )
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
    )


def _validate_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> str | None:
    """Validate answers against questions. Returns error message or None."""
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if q.required and not answer:
            return f'"{q.label}" is required.'
        if (
            q.field_type == JoinFormQuestionType.SELECT
            and answer
            and answer not in (q.options or [])
        ):
            return f'Invalid option for "{q.label}".'
    return None


def _build_custom_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> dict:
    """Snapshot answers with their labels."""
    result = {}
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if answer:
            result[q_id] = {"label": q.label, "answer": answer}
    return result


def _send_join_request_email(display_name: str, phone: str, custom_answers: dict) -> None:
    """Send vetting email for a new join request."""
    if not settings.VETTING_EMAIL:
        return
    try:
        answer_lines = "\n".join(
            f"{data['label']}: {data['answer']}" for data in custom_answers.values()
        )
        send_mail(
            subject=f"New PDA Join Request: {display_name}",
            message=f"Display Name: {display_name}\nPhone: {phone}\n\n{answer_lines}",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
        )
    except Exception:
        logger.exception("Failed to send vetting email for join request")


def _honeypot_decoy_response(display_name: str, phone_number: str) -> JoinRequestOut:
    """Mimic a real submission's shape so bots register success and stop retrying."""
    return JoinRequestOut(
        id="",
        display_name=display_name,
        phone_number=phone_number,
        submitted_at=timezone.now(),
        status=JoinRequestStatus.PENDING,
    )


def _check_phone_conflicts(validated_phone: str) -> tuple[int, str] | None:
    """Return (status_code, detail) if phone is already taken, else None."""
    from users.models import User

    if User.objects.filter(phone_number=validated_phone, archived_at__isnull=True).exists():
        return 409, "already_invited"
    if JoinRequest.objects.filter(
        phone_number=validated_phone, status=JoinRequestStatus.PENDING
    ).exists():
        return 400, "a request for this number is already pending — we'll be in touch soon"
    return None


@router.post(
    "/join-request/", response={201: JoinRequestOut, 400: ErrorOut, 409: ErrorOut}, auth=None
)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()

    # Honeypot trip — silently 201 without persisting so bots don't retry.
    if payload.website.strip():
        audit_log(
            logging.WARNING,
            "join_request_honeypot_tripped",
            request,
            details={"display_name": display_name},
        )
        return Status(201, _honeypot_decoy_response(display_name, payload.phone_number))

    name_error = validate_display_name(display_name)
    if name_error:
        return Status(400, ErrorOut(detail=name_error))

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    conflict = _check_phone_conflicts(validated_phone)
    if conflict is not None:
        code, detail = conflict
        return Status(code, ErrorOut(detail=detail))

    questions = {str(q.id): q for q in JoinFormQuestion.objects.all()}
    error = _validate_answers(payload.answers, questions)
    if error:
        return Status(400, ErrorOut(detail=error))

    custom_answers = _build_custom_answers(payload.answers, questions)

    join_request = JoinRequest.objects.create(
        display_name=display_name,
        phone_number=validated_phone,
        custom_answers=custom_answers,
    )

    logger.info("Join request submitted by %s", display_name)
    audit_log(
        logging.INFO,
        "join_request_submitted",
        request,
        target_type="join_request",
        target_id=str(join_request.id),
        details={"display_name": display_name},
    )
    _send_join_request_email(display_name, validated_phone, custom_answers)
    try:
        create_join_request_notifications(display_name)
    except Exception:
        logger.exception("Failed to create join request notifications")

    return Status(201, _join_request_out(join_request))


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=JWTAuth())
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
        return Status(403, ErrorOut(detail="Permission denied."))

    from users.models import User

    onboarded_phones = User.objects.filter(needs_onboarding=False).values_list(
        "phone_number", flat=True
    )
    join_requests = JoinRequest.objects.exclude(
        status=JoinRequestStatus.APPROVED,
        phone_number__in=onboarded_phones,
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
    response={200: ApproveJoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_request_status(request, id: UUID, payload: JoinRequestStatusIn):
    from users.api import _create_user_with_role
    from users.models import User

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
        return Status(403, ErrorOut(detail="Permission denied."))

    valid_statuses = [JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED]
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        return Status(404, ErrorOut(detail="Join request not found."))

    if join_request.status in (JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED):
        return Status(400, ErrorOut(detail="This request has already been decided."))

    _stamp_decision(join_request, payload.status, request.auth)

    magic_token = None
    user_created = False
    if payload.status == JoinRequestStatus.APPROVED:
        existing_user = User.objects.filter(phone_number=join_request.phone_number).first()
        if existing_user is None:
            _, magic_token = _create_user_with_role(
                join_request.phone_number,
                join_request.display_name,
                "",
                None,
            )
            user_created = True
        elif existing_user.archived_at is not None:
            from users._helpers import _create_magic_token

            existing_user.archived_at = None
            existing_user.needs_onboarding = True
            existing_user.save(update_fields=["archived_at", "needs_onboarding"])
            magic_token = _create_magic_token(existing_user)
            user_created = True

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

    approved_user = User.objects.filter(phone_number=join_request.phone_number).first()
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
    auth=JWTAuth(),
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
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        return Status(404, ErrorOut(detail="Join request not found."))

    if join_request.status != JoinRequestStatus.REJECTED:
        return Status(400, ErrorOut(detail="Only rejected requests can be un-rejected."))

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


@router.post("/check-phone/", response={200: CheckPhoneOut}, auth=None)
def check_phone(request, payload: CheckPhoneIn):
    from users.models import User as UserModel

    try:
        normalized = _validate_phone(payload.phone_number)
    except ValueError:
        return Status(200, CheckPhoneOut(status="unknown"))
    if UserModel.objects.filter(phone_number=normalized, archived_at__isnull=True).exists():
        return Status(200, CheckPhoneOut(status="member"))
    if JoinRequest.objects.filter(
        phone_number=normalized, status=JoinRequestStatus.PENDING
    ).exists():
        return Status(200, CheckPhoneOut(status="pending"))
    return Status(200, CheckPhoneOut(status="unknown"))
