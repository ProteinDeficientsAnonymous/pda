"""Survey CRUD, questions, and response endpoints."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from pydantic import BaseModel
from users.permissions import PermissionKey

from community._shared import ErrorOut, _authenticated_user, _optional_jwt
from community.models import (
    DatetimePollResult,
    Event,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
    SurveyVisibility,
)

router = Router()


class SurveyQuestionOut(BaseModel):
    id: str
    label: str
    field_type: str
    options: list[str] = []
    required: bool
    display_order: int


class PollResultOut(BaseModel):
    id: str
    winning_datetime: datetime
    finalized_by_id: str | None = None
    finalized_at: datetime


class TallyOut(BaseModel):
    question_id: str
    tallies: dict[str, int]
    total_responses: int


class SurveyOut(BaseModel):
    id: str
    title: str
    description: str
    slug: str
    visibility: str
    is_active: bool
    one_response_per_user: bool = False
    linked_event_id: str | None = None
    created_by_id: str | None = None
    created_at: datetime
    questions: list[SurveyQuestionOut] = []
    response_count: int = 0
    poll_result: PollResultOut | None = None
    my_response_id: str | None = None


class SurveyListOut(BaseModel):
    id: str
    title: str
    slug: str
    visibility: str
    is_active: bool
    linked_event_id: str | None = None
    created_at: datetime
    response_count: int = 0


class SurveyIn(BaseModel):
    title: str
    description: str = ""
    slug: str
    visibility: str = SurveyVisibility.PUBLIC
    is_active: bool = True
    one_response_per_user: bool = False
    linked_event_id: str | None = None


class SurveyPatchIn(BaseModel):
    title: str | None = None
    description: str | None = None
    slug: str | None = None
    visibility: str | None = None
    is_active: bool | None = None
    one_response_per_user: bool | None = None
    linked_event_id: str | None = None


class FinalizePollIn(BaseModel):
    winning_datetime: datetime


class SurveyQuestionIn(BaseModel):
    label: str
    field_type: str = SurveyQuestionType.TEXT
    options: list[str] = []
    required: bool = False


class SurveyQuestionOrderIn(BaseModel):
    question_ids: list[str]


class SurveyResponseOut(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    answers: dict
    submitted_at: datetime


class SurveyAnswersIn(BaseModel):
    answers: dict[str, str]


def _survey_question_out(q: SurveyQuestion) -> SurveyQuestionOut:
    return SurveyQuestionOut(
        id=str(q.id),
        label=q.label,
        field_type=q.field_type,
        options=q.options or [],
        required=q.required,
        display_order=q.display_order,
    )


def _poll_result_out(result: "DatetimePollResult") -> PollResultOut:
    return PollResultOut(
        id=str(result.id),
        winning_datetime=result.winning_datetime,
        finalized_by_id=str(result.finalized_by_id) if result.finalized_by_id else None,
        finalized_at=result.finalized_at,
    )


def _survey_out(
    survey: Survey,
    include_questions: bool = False,
    requesting_user=None,
) -> SurveyOut:
    questions = (
        [_survey_question_out(q) for q in survey.questions.all()] if include_questions else []
    )
    poll_result = None
    try:
        poll_result = _poll_result_out(survey.poll_result)
    except DatetimePollResult.DoesNotExist:
        pass
    my_response_id = None
    if requesting_user is not None:
        existing = survey.responses.filter(user=requesting_user).first()
        if existing:
            my_response_id = str(existing.id)
    return SurveyOut(
        id=str(survey.id),
        title=survey.title,
        description=survey.description,
        slug=survey.slug,
        visibility=survey.visibility,
        is_active=survey.is_active,
        one_response_per_user=survey.one_response_per_user,
        linked_event_id=str(survey.linked_event_id) if survey.linked_event_id else None,
        created_by_id=str(survey.created_by_id) if survey.created_by_id else None,
        created_at=survey.created_at,
        questions=questions,
        response_count=survey.responses.count(),
        poll_result=poll_result,
        my_response_id=my_response_id,
    )


def _validate_choice_answer(answer: str, q: SurveyQuestion) -> str | None:
    if answer not in (q.options or []):
        return f'Invalid option for "{q.label}".'
    return None


def _validate_multiselect_answer(answer: str, q: SurveyQuestion) -> str | None:
    for val in answer.split(","):
        if val.strip() and val.strip() not in (q.options or []):
            return f'Invalid option for "{q.label}".'
    return None


def _validate_number_answer(answer: str, q: SurveyQuestion) -> str | None:
    try:
        float(answer)
    except ValueError:
        return f'"{q.label}" must be a number.'
    return None


def _validate_yes_no_answer(answer: str, q: SurveyQuestion) -> str | None:
    if answer not in ("yes", "no"):
        return f'"{q.label}" must be yes or no.'
    return None


def _validate_rating_answer(answer: str, q: SurveyQuestion) -> str | None:
    try:
        val = int(answer)
        if val < 1 or val > 5:
            return f'"{q.label}" must be between 1 and 5.'
    except ValueError:
        return f'"{q.label}" must be a number between 1 and 5.'
    return None


def _validate_datetime_poll_answer(answer: str, q: SurveyQuestion) -> str | None:
    for val in answer.split(","):
        if val.strip() and val.strip() not in (q.options or []):
            return f'Invalid datetime option for "{q.label}".'
    return None


_SURVEY_VALIDATORS: dict[str, Callable[[str, SurveyQuestion], str | None]] = {
    SurveyQuestionType.SELECT: _validate_choice_answer,
    SurveyQuestionType.DROPDOWN: _validate_choice_answer,
    SurveyQuestionType.MULTISELECT: _validate_multiselect_answer,
    SurveyQuestionType.NUMBER: _validate_number_answer,
    SurveyQuestionType.YES_NO: _validate_yes_no_answer,
    SurveyQuestionType.RATING: _validate_rating_answer,
    SurveyQuestionType.DATETIME_POLL: _validate_datetime_poll_answer,
}


def _validate_survey_answer_value(answer: str, q: SurveyQuestion) -> str | None:
    """Validate a single answer value against its question type."""
    validator = _SURVEY_VALIDATORS.get(q.field_type)
    if validator:
        return validator(answer, q)
    return None


def _validate_survey_answers(
    answers: dict[str, str],
    questions: dict[str, SurveyQuestion],
) -> str | None:
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if q.required and not answer:
            return f'"{q.label}" is required.'
        if answer:
            error = _validate_survey_answer_value(answer, q)
            if error:
                return error
    return None


def _build_survey_answers(
    answers: dict[str, str],
    questions: dict[str, SurveyQuestion],
) -> dict:
    result = {}
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if answer:
            result[q_id] = {"label": q.label, "answer": answer}
    return result


def _apply_linked_event_update(updates: dict) -> tuple[dict, str | None]:
    """Resolve linked_event_id → linked_event object in update dict. Returns (updates, error_detail)."""
    eid = updates.pop("linked_event_id")
    if not eid:
        updates["linked_event"] = None
        return updates, None
    try:
        updates["linked_event"] = Event.objects.get(id=eid)
    except Event.DoesNotExist:
        return updates, "Event not found."
    return updates, None


# -- Admin endpoints --


@router.get(
    "/surveys/admin/",
    response={200: list[SurveyListOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_surveys_admin(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
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
        return Status(403, ErrorOut(detail="Permission denied."))
    if Survey.objects.filter(slug=payload.slug).exists():
        return Status(400, ErrorOut(detail="A survey with that slug already exists."))
    linked_event = None
    if payload.linked_event_id:
        try:
            linked_event = Event.objects.get(id=payload.linked_event_id)
        except Event.DoesNotExist:
            return Status(400, ErrorOut(detail="Event not found."))
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
    return Status(201, _survey_out(survey, include_questions=True))


@router.get(
    "/surveys/{survey_id}/admin/",
    response={200: SurveyOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_survey_admin(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        survey = Survey.objects.prefetch_related("questions").get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    return Status(200, _survey_out(survey, include_questions=True))


@router.patch(
    "/surveys/{survey_id}/",
    response={200: SurveyOut, 403: ErrorOut, 404: ErrorOut, 400: ErrorOut},
    auth=JWTAuth(),
)
def update_survey(request, survey_id: UUID, payload: SurveyPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    updates = payload.model_dump(exclude_unset=True)
    if "linked_event_id" in updates:
        updates, err = _apply_linked_event_update(updates)
        if err:
            return Status(400, ErrorOut(detail=err))
    if "slug" in updates and updates["slug"] != survey.slug:
        if Survey.objects.filter(slug=updates["slug"]).exists():
            return Status(400, ErrorOut(detail="A survey with that slug already exists."))
    for key, value in updates.items():
        setattr(survey, key, value)
    survey.save(update_fields=list(updates.keys()))
    return Status(200, _survey_out(survey, include_questions=True))


@router.delete(
    "/surveys/{survey_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_survey(request, survey_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    survey.delete()
    return Status(204, None)


# -- Survey questions --


@router.post(
    "/surveys/{survey_id}/questions/",
    response={201: SurveyQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def create_survey_question(request, survey_id: UUID, payload: SurveyQuestionIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    max_order = survey.questions.count()
    q = SurveyQuestion.objects.create(
        survey=survey,
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=max_order,
    )
    return Status(201, _survey_question_out(q))


@router.patch(
    "/surveys/{survey_id}/questions/{question_id}/",
    response={200: SurveyQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_survey_question(request, survey_id: UUID, question_id: UUID, payload: SurveyQuestionIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = SurveyQuestion.objects.get(id=question_id, survey_id=survey_id)
    except SurveyQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    q.label = payload.label
    q.field_type = payload.field_type
    q.options = payload.options
    q.required = payload.required
    q.save()
    return Status(200, _survey_question_out(q))


@router.delete(
    "/surveys/{survey_id}/questions/{question_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_survey_question(request, survey_id: UUID, question_id: UUID):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = SurveyQuestion.objects.get(id=question_id, survey_id=survey_id)
    except SurveyQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    q.delete()
    return Status(204, None)


@router.put(
    "/surveys/{survey_id}/questions/order/",
    response={200: list[SurveyQuestionOut], 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reorder_survey_questions(request, survey_id: UUID, payload: SurveyQuestionOrderIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    for idx, qid in enumerate(payload.question_ids):
        SurveyQuestion.objects.filter(id=qid, survey_id=survey_id).update(display_order=idx)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        survey = Survey.objects.get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
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


def _response_out(response: SurveyResponse, user_name: str | None) -> SurveyResponseOut:
    return SurveyResponseOut(
        id=str(response.id),
        user_id=str(response.user_id) if response.user_id else None,
        user_name=user_name,
        answers=response.answers,
        submitted_at=response.submitted_at,
    )


def _tally_question(q: SurveyQuestion, responses: list[SurveyResponse]) -> TallyOut:
    counts: dict[str, int] = {opt: 0 for opt in (q.options or [])}
    for r in responses:
        answer_data = r.answers.get(str(q.id))
        if not answer_data:
            continue
        for val in answer_data.get("answer", "").split(","):
            val = val.strip()
            if val in counts:
                counts[val] += 1
    return TallyOut(
        question_id=str(q.id),
        tallies=counts,
        total_responses=len(responses),
    )


def _has_finalize_permission(request, survey: Survey, event: Event | None) -> bool:
    if request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return True
    if request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if survey.created_by_id == request.auth.pk:
        return True
    if event and event.created_by_id == request.auth.pk:
        return True
    if event and event.co_hosts.filter(pk=request.auth.pk).exists():
        return True
    return False


# -- Public endpoints --


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
            return Status(200, _response_out(existing, user_name))
    response = SurveyResponse.objects.create(survey=survey, user=auth_user, answers=answers)
    return Status(201, _response_out(response, user_name))


@router.get(
    "/surveys/{survey_id}/tallies/",
    response={200: list[TallyOut], 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_survey_tallies(request, survey_id: UUID):
    try:
        survey = Survey.objects.prefetch_related("questions", "responses").get(id=survey_id)
    except Survey.DoesNotExist:
        return Status(404, ErrorOut(detail="Survey not found."))
    poll_questions = [
        q for q in survey.questions.all() if q.field_type == SurveyQuestionType.DATETIME_POLL
    ]
    responses = list(survey.responses.all())
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

    survey.refresh_from_db()
    return Status(200, _survey_out(survey, include_questions=True, requesting_user=request.auth))
