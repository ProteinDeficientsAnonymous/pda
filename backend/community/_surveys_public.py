"""Public survey response and poll tally endpoints."""

import logging
import secrets
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log, mark_request_anonymized
from config.auth import gated_jwt
from config.ratelimit import auth_or_ip_key, rate_limit
from django.db import transaction
from ninja import Router
from ninja.responses import Status
from notifications._survey_response_notifications import notify_survey_response
from users._helpers import visible_display_name

from community._shared import ErrorOut, _authenticated_user, _optional_jwt
from community._survey_helpers import (
    _has_finalize_permission,
    _response_to_update,
    _submit_out,
    _survey_out,
    _tally_question,
    survey_is_open,
)
from community._survey_schemas import (
    PollResultsOut,
    SurveyAnswersIn,
    SurveyOut,
    SurveySubmitOut,
)
from community._survey_validators import _build_survey_answers, _validate_survey_answers
from community._validation import Code, raise_validation
from community.models import (
    Survey,
    SurveyQuestionType,
    SurveyResponse,
    SurveyVisibility,
)

router = Router()


def _visible_survey_or_404(slug: str, auth_user, *, for_update: bool = False) -> Survey:
    # Closed surveys still resolve so the UI can render a closed state.
    qs = Survey.objects.prefetch_related("questions")
    if for_update:
        qs = qs.select_for_update()
    try:
        survey = qs.get(slug=slug)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    if survey.visibility == SurveyVisibility.MEMBERS_ONLY and auth_user is None:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    # Feedback surveys are only answerable through a per-attendee token link.
    if survey.feedback_event_type:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    return survey


@router.get(
    "/surveys/view/{slug}/",
    response={200: SurveyOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def get_survey_public(request, slug: str, response_token: str = ""):
    auth_user = _authenticated_user(request.auth)
    survey = _visible_survey_or_404(slug, auth_user)
    return Status(
        200,
        _survey_out(
            survey,
            include_questions=True,
            requesting_user=auth_user,
            response_token=response_token,
        ),
    )


@router.post(
    "/surveys/view/{slug}/respond/",
    response={
        200: SurveySubmitOut,
        201: SurveySubmitOut,
        400: ErrorOut,
        404: ErrorOut,
        429: ErrorOut,
    },
    auth=_optional_jwt,
)
@rate_limit(key_func=auth_or_ip_key, rate="20/h")
def submit_survey_response(
    request,
    slug: str,
    payload: SurveyAnswersIn,
    response_token: str = "",
    response_id: UUID | None = None,
):
    auth_user = _authenticated_user(request.auth)
    # select_for_update() serializes concurrent submits against the same survey row,
    # so the max_responses check-then-create can't race past the cap (issue #1465).
    with transaction.atomic():
        survey = _visible_survey_or_404(slug, auth_user, for_update=True)
        # No responder on an anonymous survey; members dedupe by response token instead.
        response_user = None if survey.anonymous else auth_user
        if survey.anonymous:
            # Audit rows and request log lines would re-link the submitter by timestamp.
            mark_request_anonymized(request)
        existing = _response_to_update(survey, response_user, response_token, response_id)
        if not survey_is_open(survey, check_cap=existing is None):
            raise_validation(Code.Survey.CLOSED, status_code=400)
        questions = {str(q.id): q for q in survey.questions.all()}
        _validate_survey_answers(payload.answers, questions)
        answers = _build_survey_answers(payload.answers, questions)
        user_name = visible_display_name(auth_user, auth_user) if response_user else None
        target = AuditTarget(type=AuditTargetType.SURVEY, id=str(survey.id), details={"slug": slug})
        if existing:
            existing.answers = answers
            existing.save(update_fields=["answers"])
            audit_log(logging.INFO, "survey_response_updated", request, target=target)
            return Status(200, _submit_out(existing, user_name))
        # without a member link the token is the only way back to this row for editing
        anonymous_token = secrets.token_urlsafe(32) if response_user is None else None
        response = SurveyResponse.objects.create(
            survey=survey, user=response_user, answers=answers, anonymous_token=anonymous_token
        )
        audit_log(logging.INFO, "survey_response_submitted", request, target=target)
        transaction.on_commit(lambda: notify_survey_response(survey, response_user))
        return Status(201, _submit_out(response, user_name))


@router.get(
    "/surveys/{survey_id}/tallies/",
    response={200: list[PollResultsOut], 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_survey_tallies(request, survey_id: UUID):
    try:
        survey = Survey.objects.prefetch_related("questions").get(id=survey_id)
    except Survey.DoesNotExist:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)

    # Tallies expose voter names/photos — gate to MANAGE_SURVEYS / MANAGE_EVENTS /
    # survey owner. Without this any authed user could enumerate voters by UUID.
    if not _has_finalize_permission(request, survey):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(
                type=AuditTargetType.SURVEY,
                id=str(survey_id),
                details={"endpoint": "get_survey_tallies"},
            ),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="get_survey_tallies")

    poll_questions = [
        q for q in survey.questions.all() if q.field_type == SurveyQuestionType.DATETIME_POLL
    ]
    responses = list(survey.responses.select_related("user").all())
    tallies = [
        _tally_question(q, responses, request.auth, include_voters=not survey.anonymous)
        for q in poll_questions
    ]
    return Status(200, tallies)
