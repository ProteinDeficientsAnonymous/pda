"""Join form configuration endpoints (question CRUD and ordering)."""

import logging
from uuid import UUID

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel, Field
from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._shared import ErrorOut, logger  # noqa: F401
from community.models import JoinFormQuestion, JoinFormQuestionType

router = Router()


class JoinFormQuestionOut(BaseModel):
    id: str
    label: str
    field_type: str
    options: list[str] = []
    required: bool
    display_order: int


class JoinFormQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: str = Field(default=JoinFormQuestionType.TEXT, max_length=FieldLimit.CHOICE)
    options: list[str] = []
    required: bool = False


class JoinFormQuestionOrderIn(BaseModel):
    question_ids: list[str]


def _question_out(q: JoinFormQuestion) -> JoinFormQuestionOut:
    return JoinFormQuestionOut(
        id=str(q.id),
        label=q.label,
        field_type=q.field_type,
        options=q.options or [],
        required=q.required,
        display_order=q.display_order,
    )


@router.get("/join-form/", response={200: list[JoinFormQuestionOut]}, auth=None)
def get_join_form(request):
    questions = JoinFormQuestion.objects.all()
    return Status(200, [_question_out(q) for q in questions])


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
    return Status(201, _question_out(q))


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
    return Status(200, _question_out(q))


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
    return Status(200, [_question_out(q) for q in questions])
