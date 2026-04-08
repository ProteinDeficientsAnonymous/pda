"""Public survey response and poll tally endpoints."""

import logging
from uuid import UUID

from config.audit import audit_log
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from community._shared import ErrorOut, _authenticated_user, _optional_jwt
from community._survey_helpers import (
    _has_finalize_permission,
    _response_out,
    _survey_out,
    _tally_question,
)
from community._survey_schemas import (
    FinalizePollIn,
    PollResultsOut,
    SurveyAnswersIn,
    SurveyOut,
    SurveyResponseOut,
)
from community._survey_validators import _build_survey_answers, _validate_survey_answers
from community.models import (
    DatetimePollResult,
    Survey,
    SurveyQuestionType,
    SurveyResponse,
    SurveyVisibility,
)

router = Router()


@router.get(
    "/surveys/view/{slug}/",
    response={200: SurveyOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def get_survey_public(request, slug: str):
    try:
        survey = Survey.objects.prefetch_related("questions").get(slug=slug, is_active=True)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    auth_user = _authenticated_user(request.auth)
    if survey.visibility == SurveyVisibility.MEMBERS_ONLY and auth_user is None:
        return Status(404, ErrorOut(detail="Survey not found."))
    return Status(200, _survey_out(survey, include_questions=True, requesting_user=auth_user))


@router.post(
    "/surveys/view/{slug}/respond/",
    response={200: SurveyResponseOut, 201: SurveyResponseOut, 400: ErrorOut, 404: ErrorOut},
    auth=_optional_jwt,
)
def submit_survey_response(request, slug: str, payload: SurveyAnswersIn):
    try:
        survey = Survey.objects.prefetch_related("questions").get(slug=slug, is_active=True)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    auth_user = _authenticated_user(request.auth)
    if survey.visibility == SurveyVisibility.MEMBERS_ONLY and auth_user is None:
        return Status(404, ErrorOut(detail="Survey not found."))
    questions = {str(q.id): q for q in survey.questions.all()}
    error = _validate_survey_answers(payload.answers, questions)
    if error:
        return Status(400, ErrorOut(detail=error))
    answers = _build_survey_answers(payload.answers, questions)
    user_name = (auth_user.display_name or auth_user.phone_number) if auth_user else None
    if survey.one_response_per_user and auth_user is not None:
        existing = SurveyResponse.objects.filter(survey=survey, user=auth_user).first()
        if existing:
            existing.answers = answers
            existing.save(update_fields=["answers"])
            audit_log(
                logging.INFO,
                "survey_response_updated",
                request,
                target_type="survey",
                target_id=str(survey.id),
                details={"slug": slug},
            )
            return Status(200, _response_out(existing, user_name))
    response = SurveyResponse.objects.create(survey=survey, user=auth_user, answers=answers)
    audit_log(
        logging.INFO,
        "survey_response_submitted",
        request,
        target_type="survey",
        target_id=str(survey.id),
        details={"slug": slug},
    )
    return Status(201, _response_out(response, user_name))


@router.get(
    "/surveys/{survey_id}/tallies/",
    response={200: list[PollResultsOut], 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_survey_tallies(request, survey_id: UUID):
    try:
        survey = Survey.objects.prefetch_related("questions").get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    poll_questions = [
        q for q in survey.questions.all() if q.field_type == SurveyQuestionType.DATETIME_POLL
    ]
    responses = list(survey.responses.select_related("user").all())
    tallies = [_tally_question(q, responses) for q in poll_questions]
    return Status(200, tallies)


@router.post(
    "/surveys/{survey_id}/finalize/",
    response={200: SurveyOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def finalize_poll(request, survey_id: UUID, payload: FinalizePollIn):
    try:
        survey = (
            Survey.objects.select_related("linked_event", "created_by")
            .prefetch_related("questions")
            .get(id=survey_id)
        )
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))

    event = survey.linked_event
    if not _has_finalize_permission(request, survey, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="survey",
            target_id=str(survey_id),
            details={"endpoint": "finalize_poll"},
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    if hasattr(survey, "poll_result"):
        return Status(400, ErrorOut(detail="This poll has already been finalized."))

    poll_questions = [
        q for q in survey.questions.all() if q.field_type == SurveyQuestionType.DATETIME_POLL
    ]
    if not poll_questions:
        return Status(400, ErrorOut(detail="Survey has no datetime poll question."))

    winning_iso = payload.winning_datetime.isoformat()
    all_options = poll_questions[0].options or []
    if winning_iso not in all_options:
        return Status(400, ErrorOut(detail="Winning datetime is not one of the poll options."))

    DatetimePollResult.objects.create(
        survey=survey,
        winning_datetime=payload.winning_datetime,
        finalized_by=request.auth,
    )
    survey.is_active = False
    survey.save(update_fields=["is_active"])

    if event:
        event.start_datetime = payload.winning_datetime
        event.datetime_tbd = False
        event.save(update_fields=["start_datetime", "datetime_tbd"])

    audit_log(
        logging.INFO,
        "survey_poll_finalized",
        request,
        target_type="survey",
        target_id=str(survey_id),
        details={
            "winning_datetime": payload.winning_datetime.isoformat(),
            "linked_event_id": str(event.id) if event else None,
        },
    )
    survey.refresh_from_db()
    return Status(200, _survey_out(survey, include_questions=True, requesting_user=request.auth))
