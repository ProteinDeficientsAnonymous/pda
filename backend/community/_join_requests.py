"""Join form configuration, join request submission/management, and check-phone endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from config.audit import audit_log
from django.conf import settings
from django.core.mail import send_mail
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._shared import DISPLAY_NAME_RE, ErrorOut, _validate_phone, logger
from community.models import (
    JoinFormQuestion,
    JoinFormQuestionType,
    JoinRequest,
    JoinRequestStatus,
)

router = Router()


class JoinRequestIn(BaseModel):
    display_name: str
    phone_number: str
    answers: dict[str, str] = {}


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


class JoinFormQuestionOut(BaseModel):
    id: str
    label: str
    field_type: str
    options: list[str] = []
    required: bool
    display_order: int


class JoinFormQuestionIn(BaseModel):
    label: str
    field_type: str = JoinFormQuestionType.TEXT
    options: list[str] = []
    required: bool = False


class JoinFormQuestionOrderIn(BaseModel):
    question_ids: list[str]


class JoinRequestStatusIn(BaseModel):
    status: str


class ApproveJoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    status: str
    magic_link_token: str | None = None


class CheckPhoneOut(BaseModel):
    status: str  # "member" | "pending" | "unknown"


class CheckPhoneIn(BaseModel):
    phone_number: str


def _join_request_out(jr: JoinRequest) -> JoinRequestOut:
    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    return JoinRequestOut(
        id=str(jr.id),
        display_name=jr.display_name,
        phone_number=jr.phone_number,
        answers=answers,
        submitted_at=jr.submitted_at,
        status=jr.status,
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


# ---------------------------------------------------------------------------
# Join form configuration
# ---------------------------------------------------------------------------


@router.get("/join-form/", response={200: list[JoinFormQuestionOut]}, auth=None)
def get_join_form(request):
    questions = JoinFormQuestion.objects.all()
    return Status(
        200,
        [
            JoinFormQuestionOut(
                id=str(q.id),
                label=q.label,
                field_type=q.field_type,
                options=q.options or [],
                required=q.required,
                display_order=q.display_order,
            )
            for q in questions
        ],
    )


@router.post(
    "/join-form/questions/",
    response={201: JoinFormQuestionOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_join_form_question(request, payload: JoinFormQuestionIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "create_join_form_question",
                "required_permission": PermissionKey.EDIT_JOIN_QUESTIONS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    max_order = JoinFormQuestion.objects.count()
    q = JoinFormQuestion.objects.create(
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=max_order,
    )
    audit_log(
        logging.INFO,
        "join_form_question_created",
        request,
        target_type="join_form_question",
        target_id=str(q.id),
        details={"label": q.label},
    )
    return Status(
        201,
        JoinFormQuestionOut(
            id=str(q.id),
            label=q.label,
            field_type=q.field_type,
            options=q.options or [],
            required=q.required,
            display_order=q.display_order,
        ),
    )


@router.patch(
    "/join-form/questions/{question_id}/",
    response={200: JoinFormQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_form_question(request, question_id: UUID, payload: JoinFormQuestionIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="join_form_question",
            target_id=str(question_id),
            details={
                "endpoint": "update_join_form_question",
                "required_permission": PermissionKey.EDIT_JOIN_QUESTIONS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = JoinFormQuestion.objects.get(id=question_id)
    except JoinFormQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    q.label = payload.label
    q.field_type = payload.field_type
    q.options = payload.options
    q.required = payload.required
    q.save()
    audit_log(
        logging.INFO,
        "join_form_question_updated",
        request,
        target_type="join_form_question",
        target_id=str(question_id),
        details={"label": q.label},
    )
    return Status(
        200,
        JoinFormQuestionOut(
            id=str(q.id),
            label=q.label,
            field_type=q.field_type,
            options=q.options or [],
            required=q.required,
            display_order=q.display_order,
        ),
    )


@router.delete(
    "/join-form/questions/{question_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_join_form_question(request, question_id: UUID):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="join_form_question",
            target_id=str(question_id),
            details={
                "endpoint": "delete_join_form_question",
                "required_permission": PermissionKey.EDIT_JOIN_QUESTIONS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = JoinFormQuestion.objects.get(id=question_id)
    except JoinFormQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    label = q.label
    q.delete()
    audit_log(
        logging.INFO,
        "join_form_question_deleted",
        request,
        target_type="join_form_question",
        target_id=str(question_id),
        details={"label": label},
    )
    return Status(204, None)


@router.put(
    "/join-form/questions/order/",
    response={200: list[JoinFormQuestionOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_join_form_questions(request, payload: JoinFormQuestionOrderIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "reorder_join_form_questions",
                "required_permission": PermissionKey.EDIT_JOIN_QUESTIONS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    for idx, qid in enumerate(payload.question_ids):
        JoinFormQuestion.objects.filter(id=qid).update(display_order=idx)
    audit_log(logging.INFO, "join_form_questions_reordered", request)
    questions = JoinFormQuestion.objects.all()
    return Status(
        200,
        [
            JoinFormQuestionOut(
                id=str(q.id),
                label=q.label,
                field_type=q.field_type,
                options=q.options or [],
                required=q.required,
                display_order=q.display_order,
            )
            for q in questions
        ],
    )


# ---------------------------------------------------------------------------
# Join request submission
# ---------------------------------------------------------------------------


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()
    if not display_name:
        return Status(400, ErrorOut(detail="display_name is required."))
    if not DISPLAY_NAME_RE.match(display_name) or len(display_name) > 64:
        return Status(
            400,
            ErrorOut(detail="Display name must contain only letters and spaces (max 64 chars)."),
        )

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

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

    join_requests = JoinRequest.objects.all()
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

    return Status(
        200,
        ApproveJoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            status=join_request.status,
            magic_link_token=magic_token,
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
