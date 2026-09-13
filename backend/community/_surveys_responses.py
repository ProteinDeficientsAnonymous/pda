"""Admin survey response listing and deletion endpoints."""

import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._shared import ErrorOut
from community._survey_schemas import SurveyResponseOut
from community._validation import Code, raise_validation
from community.models import Survey, SurveyResponse

router = Router()


@router.get(
    "/surveys/{survey_id}/responses/",
    response={200: list[SurveyResponseOut], 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def list_survey_responses(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.SURVEY,
                id=str(survey_id),
                details={
                    "endpoint": "list_survey_responses",
                    "required_permission": PermissionKey.MANAGE_SURVEYS,
                },
            ),
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
                user_name=visible_display_name(r.user, request.auth) if r.user else None,
                answers=r.answers,
                submitted_at=r.submitted_at,
            )
            for r in responses
        ],
    )


@router.delete(
    "/surveys/{survey_id}/responses/{response_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_survey_response(request, survey_id: UUID, response_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.SURVEY,
                id=str(survey_id),
                details={
                    "endpoint": "delete_survey_response",
                    "response_id": str(response_id),
                    "required_permission": PermissionKey.MANAGE_SURVEYS,
                },
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="manage_surveys")
    try:
        response = SurveyResponse.objects.get(id=response_id, survey_id=survey_id)
    except SurveyResponse.DoesNotExist:
        raise_validation(Code.Survey.RESPONSE_NOT_FOUND, status_code=404)
    response.delete()
    audit_log(
        logging.INFO,
        "survey_response_deleted",
        request,
        target=AuditTarget(
            type=AuditTargetType.SURVEY,
            id=str(survey_id),
            details={"response_id": str(response_id)},
        ),
    )
    return Status(204, None)
