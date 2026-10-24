import logging

from config.audit import AuditTarget, AuditTargetType, audit_log, mark_request_anonymized
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ninja import Header, Router
from ninja.responses import Status
from notifications._event_feedback_notifications import notify_event_feedback

from community._event_feedback_schemas import EventFeedbackOut, EventFeedbackSubmitOut
from community._shared import ErrorOut
from community._survey_helpers import _survey_out, survey_is_open
from community._survey_schemas import SurveyAnswersIn, SurveyOut
from community._survey_validators import _build_survey_answers, _validate_survey_answers
from community._validation import Code, raise_validation
from community.models import EventFeedbackRequest, EventStatus, Survey, SurveyResponse
from community.models.event_feedback import feedback_survey_for

router = Router()


# Header, not path/query: request log lines record the URL with a timestamp.
FeedbackToken = Header("", alias="X-Feedback-Token")
_MAX_TOKEN_LENGTH = EventFeedbackRequest._meta.get_field("token").max_length or 64


def _feedback_request_or_404(token: str, *, for_update: bool = False) -> EventFeedbackRequest:
    if not token or len(token) > _MAX_TOKEN_LENGTH:
        raise_validation(Code.Survey.FEEDBACK_LINK_INVALID, status_code=404)
    qs = EventFeedbackRequest.objects.select_related("event")
    if for_update:
        qs = qs.select_for_update(of=("self",))
    try:
        return qs.get(token=token)
    except EventFeedbackRequest.DoesNotExist:
        raise_validation(Code.Survey.FEEDBACK_LINK_INVALID, status_code=404)


def _public_survey_out(survey: Survey) -> SurveyOut:
    # token holders are unauthenticated: hide live counts and admin-only metadata
    return _survey_out(survey, include_questions=True).model_copy(
        update={
            "slug": "",
            "response_count": 0,
            "max_responses": None,
            "linked_event_id": None,
            "created_by_id": None,
        }
    )


@router.get(
    "/event-feedback/",
    response={200: EventFeedbackOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="60/h")
def get_event_feedback(request, token: str = FeedbackToken):
    # Even a session-authed viewer stays out of the log: view time hints at submit time.
    mark_request_anonymized(request)
    feedback_request = _feedback_request_or_404(token)
    event = feedback_request.event
    survey = feedback_survey_for(event.event_type)
    return Status(
        200,
        EventFeedbackOut(
            survey=_public_survey_out(survey) if survey else None,
            event_id=str(event.id),
            event_title=event.title,
            event_start=event.start_datetime,
            already_responded=feedback_request.responded_on is not None,
            is_open=(
                survey is not None and event.status == EventStatus.ACTIVE and survey_is_open(survey)
            ),
        ),
    )


def _open_feedback_survey(feedback_request: EventFeedbackRequest) -> Survey:
    if feedback_request.responded_on is not None:
        raise_validation(Code.Survey.FEEDBACK_ALREADY_SUBMITTED, status_code=400)
    if feedback_request.event.status != EventStatus.ACTIVE:
        raise_validation(Code.Survey.CLOSED, status_code=400)
    # Survey row lock serializes the max_responses check-then-create across tokens.
    survey = (
        Survey.objects.select_for_update()
        .filter(feedback_event_type=feedback_request.event.event_type)
        .first()
    )
    if survey is None:
        raise_validation(Code.Survey.NOT_FOUND, status_code=404)
    if not survey_is_open(survey):
        raise_validation(Code.Survey.CLOSED, status_code=400)
    return survey


@router.post(
    "/event-feedback/respond/",
    response={
        201: EventFeedbackSubmitOut,
        400: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
        429: ErrorOut,
    },
    auth=None,
)
@rate_limit(key_func=client_ip, rate="20/h")
def submit_event_feedback(request, payload: SurveyAnswersIn, token: str = FeedbackToken):
    mark_request_anonymized(request)
    with transaction.atomic():
        # Row lock: a forwarded link or double-click must yield exactly one response.
        feedback_request = _feedback_request_or_404(token, for_update=True)
        survey = _open_feedback_survey(feedback_request)
        questions = {str(q.id): q for q in survey.questions.all()}
        _validate_survey_answers(payload.answers, questions)
        SurveyResponse.objects.create(
            survey=survey,
            user=None,
            event=feedback_request.event,
            answers=_build_survey_answers(payload.answers, questions),
        )
        feedback_request.responded_on = timezone.localdate(timezone=settings.COMMUNITY_TZ)
        feedback_request.save(update_fields=["responded_on"])
        audit_log(
            logging.INFO,
            "survey_response_submitted",
            request,
            target=AuditTarget(type=AuditTargetType.SURVEY, id=str(survey.id)),
        )
        event = feedback_request.event
        transaction.on_commit(lambda: notify_event_feedback(event))
    return Status(201, EventFeedbackSubmitOut(confirmation_message=survey.confirmation_message))
