"""Join request submission, management, and check-phone endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from config.audit import audit_log
from django.conf import settings
from django.core.mail import send_mail
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
    return JoinRequestOut(
        id=str(jr.id),
        display_name=jr.display_name,
        phone_number=jr.phone_number,
        answers=answers,
        submitted_at=jr.submitted_at,
        status=jr.status,
        user_id=str(user.id) if user else None,
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


@router.post(
    "/join-request/", response={201: JoinRequestOut, 400: ErrorOut, 409: ErrorOut}, auth=None
)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()
    name_error = validate_display_name(display_name)
    if name_error:
        return Status(400, ErrorOut(detail=name_error))

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    from users.models import User

    if User.objects.filter(phone_number=validated_phone).exists():
        return Status(409, ErrorOut(detail="already_invited"))

    if JoinRequest.objects.filter(
        phone_number=validated_phone, status=JoinRequestStatus.PENDING
    ).exists():
        return Status(
            400,
            ErrorOut(
                detail="a request for this number is already pending — we'll be in touch soon"
            ),
        )

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

    if join_request.status == JoinRequestStatus.APPROVED:
        return Status(400, ErrorOut(detail="This request has already been approved."))

    join_request.status = payload.status
    join_request.save()

    magic_token = None
    user_created = False
    if payload.status == JoinRequestStatus.APPROVED:
        if not User.objects.filter(phone_number=join_request.phone_number).exists():
            _, magic_token = _create_user_with_role(
                join_request.phone_number,
                join_request.display_name,
                "",
                None,
            )
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


@router.post("/check-phone/", response={200: CheckPhoneOut}, auth=None)
def check_phone(request, payload: CheckPhoneIn):
    from users.models import User as UserModel

    try:
        normalized = _validate_phone(payload.phone_number)
    except ValueError:
        return Status(200, CheckPhoneOut(status="unknown"))
    if UserModel.objects.filter(phone_number=normalized).exists():
        return Status(200, CheckPhoneOut(status="member"))
    if JoinRequest.objects.filter(
        phone_number=normalized, status=JoinRequestStatus.PENDING
    ).exists():
        return Status(200, CheckPhoneOut(status="pending"))
    return Status(200, CheckPhoneOut(status="unknown"))


class RequestLoginLinkIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)


class RequestLoginLinkOut(BaseModel):
    detail: str


_REQUEST_LINK_RESPONSE = "if you've been invited, an admin will be in touch with your login link"


@router.post("/request-login-link/", response={200: RequestLoginLinkOut}, auth=None)
def request_login_link(request, payload: RequestLoginLinkIn):
    """Unauthenticated endpoint for invited users to re-request a magic login link.

    Always returns 200 to prevent phone number enumeration.
    If a User exists, generates a magic link token and notifies admins.
    """
    from datetime import timedelta

    from django.utils import timezone
    from notifications.service import create_magic_link_request_notifications
    from users._helpers import _create_magic_token
    from users.models import MagicLoginToken, User

    try:
        normalized = _validate_phone(payload.phone_number)
    except ValueError:
        return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))

    user = User.objects.filter(phone_number=normalized).first()
    if user:
        recent_token_exists = MagicLoginToken.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(minutes=5),
        ).exists()
        if not recent_token_exists:
            _create_magic_token(user)
            try:
                create_magic_link_request_notifications(user)
            except Exception:
                logger.exception("Failed to create magic link request notifications")

    return Status(200, RequestLoginLinkOut(detail=_REQUEST_LINK_RESPONSE))
