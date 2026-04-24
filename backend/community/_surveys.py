"""Survey CRUD, questions, and response endpoints."""

import logging
from uuid import UUID

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._shared import ErrorOut
from community._survey_helpers import (
    _apply_linked_event_update,
    _survey_out,
    _survey_question_out,
)
from community._survey_schemas import (
    SurveyIn,
    SurveyListOut,
    SurveyOut,
    SurveyPatchIn,
    SurveyQuestionIn,
    SurveyQuestionOrderIn,
    SurveyQuestionOut,
    SurveyResponseOut,
)
from community._validation import Code, raise_validation
from community.models import (
    Event,
    Survey,
    SurveyQuestion,
)

router = Router()


# -- Admin endpoints --


@router.get(
    "/surveys/admin/",
    response={200: list[SurveyListOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_surveys_admin(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "list_surveys_admin",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    surveys = Survey.objects.all()
    return Status(
        200,
        [
            SurveyListOut(
                id=str(s.id),
                title=s.title,
                slug=s.slug,
                visibility=s.visibility,
                is_active=s.is_active,
                linked_event_id=str(s.linked_event_id) if s.linked_event_id else None,
                created_at=s.created_at,
                response_count=s.responses.count(),
            )
            for s in surveys
        ],
    )


@router.post(
    "/surveys/",
    response={201: SurveyOut, 403: ErrorOut, 400: ErrorOut},
    auth=JWTAuth(),
)
def create_survey(request, payload: SurveyIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "create_survey",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    if Survey.objects.filter(slug=payload.slug).exists():
        raise_validation(Code.Survey.SLUG_ALREADY_EXISTS, field="slug", status_code=400)
    linked_event = None
    if payload.linked_event_id:
        try:
            linked_event = Event.objects.get(id=payload.linked_event_id)
        except Event.DoesNotExist:
            raise_validation(Code.Event.NOT_FOUND, field="linked_event_id", status_code=400)
    survey = Survey.objects.create(
        title=payload.title,
        description=payload.description,
        slug=payload.slug,
        visibility=payload.visibility,
        is_active=payload.is_active,
        one_response_per_user=payload.one_response_per_user,
        linked_event=linked_event,
        created_by=request.auth,
    )
    audit_log(
        logging.INFO,
        "survey_created",
        request,
        target_type="survey",
        target_id=str(survey.id),
        details={"title": survey.title, "slug": survey.slug},
    )
    return Status(201, _survey_out(survey, include_questions=True))


@router.get(
    "/surveys/{survey_id}/admin/",
    response={200: SurveyOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_survey_admin(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "get_survey_admin",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        survey = Survey.objects.prefetch_related("questions").get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    return Status(200, _survey_out(survey, include_questions=True))


@router.patch(
    "/surveys/{survey_id}/",
    response={200: SurveyOut, 403: ErrorOut, 404: ErrorOut, 400: ErrorOut},
    auth=JWTAuth(),
)
def update_survey(request, survey_id: UUID, payload: SurveyPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "update_survey",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    updates = payload.model_dump(exclude_unset=True)
    if "linked_event_id" in updates:
        updates = _apply_linked_event_update(updates)
    if "slug" in updates and updates["slug"] != survey.slug:
        if Survey.objects.filter(slug=updates["slug"]).exists():
            raise_validation(Code.Survey.SLUG_ALREADY_EXISTS, field="slug", status_code=400)
    for key, value in updates.items():
        setattr(survey, key, value)
    survey.save(update_fields=list(updates.keys()))
    audit_log(
        logging.INFO,
        "survey_updated",
        request,
        target_type="survey",
        target_id=str(survey_id),
        details={"fields_changed": list(updates.keys())},
    )
    return Status(200, _survey_out(survey, include_questions=True))


@router.delete(
    "/surveys/{survey_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_survey(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "delete_survey",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    title = survey.title
    survey.delete()
    audit_log(
        logging.WARNING,
        "survey_deleted",
        request,
        target_type="survey",
        target_id=str(survey_id),
        details={"title": title},
    )
    return Status(204, None)


# -- Survey questions --


@router.post(
    "/surveys/{survey_id}/questions/",
    response={201: SurveyQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def create_survey_question(request, survey_id: UUID, payload: SurveyQuestionIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "create_survey_question",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    max_order = survey.questions.count()
    q = SurveyQuestion.objects.create(
        survey=survey,
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=max_order,
    )
    audit_log(
        logging.INFO,
        "survey_question_created",
        request,
        target_type="survey_question",
        target_id=str(q.id),
        details={"survey_id": str(survey_id), "label": q.label},
    )
    return Status(201, _survey_question_out(q))


@router.patch(
    "/surveys/{survey_id}/questions/{question_id}/",
    response={200: SurveyQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_survey_question(request, survey_id: UUID, question_id: UUID, payload: SurveyQuestionIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey_question",
            target_id=str(question_id),
            details={
                "endpoint": "update_survey_question",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        q = SurveyQuestion.objects.get(id=question_id, survey_id=survey_id)
    except SurveyQuestion.DoesNotExist:
        raise_validation(Code.Survey.QUESTION_NOT_FOUND, status_code=404)
    q.label = payload.label
    q.field_type = payload.field_type
    q.options = payload.options
    q.required = payload.required
    q.save()
    audit_log(
        logging.INFO,
        "survey_question_updated",
        request,
        target_type="survey_question",
        target_id=str(question_id),
        details={"survey_id": str(survey_id), "label": q.label},
    )
    return Status(200, _survey_question_out(q))


@router.delete(
    "/surveys/{survey_id}/questions/{question_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_survey_question(request, survey_id: UUID, question_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey_question",
            target_id=str(question_id),
            details={
                "endpoint": "delete_survey_question",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        q = SurveyQuestion.objects.get(id=question_id, survey_id=survey_id)
    except SurveyQuestion.DoesNotExist:
        raise_validation(Code.Survey.QUESTION_NOT_FOUND, status_code=404)
    q.delete()
    audit_log(
        logging.INFO,
        "survey_question_deleted",
        request,
        target_type="survey_question",
        target_id=str(question_id),
        details={"survey_id": str(survey_id)},
    )
    return Status(204, None)


@router.put(
    "/surveys/{survey_id}/questions/order/",
    response={200: list[SurveyQuestionOut], 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reorder_survey_questions(request, survey_id: UUID, payload: SurveyQuestionOrderIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "reorder_survey_questions",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    for idx, qid in enumerate(payload.question_ids):
        SurveyQuestion.objects.filter(id=qid, survey_id=survey_id).update(display_order=idx)
    audit_log(
        logging.INFO,
        "survey_questions_reordered",
        request,
        target_type="survey",
        target_id=str(survey_id),
    )
    questions = SurveyQuestion.objects.filter(survey_id=survey_id)
    return Status(200, [_survey_question_out(q) for q in questions])


# -- Survey responses (admin) --


@router.get(
    "/surveys/{survey_id}/responses/",
    response={200: list[SurveyResponseOut], 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def list_survey_responses(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={
                "endpoint": "list_survey_responses",
                "required_permission": PermissionKey.MANAGE_SURVEYS,
            },
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    responses = survey.responses.select_related("user").all()
    return Status(
        200,
        [
            SurveyResponseOut(
                id=str(r.id),
                user_id=str(r.user_id) if r.user_id else None,
                user_name=(r.user.display_name or r.user.phone_number) if r.user else None,
                answers=r.answers,
                submitted_at=r.submitted_at,
            )
            for r in responses
        ],
    )
