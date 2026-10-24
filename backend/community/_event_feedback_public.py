import logging

from config.audit import AuditTarget, AuditTargetType, audit_log, mark_request_anonymized
from config.ratelimit import rate_limit
from django.db import transaction
from django.utils import timezone
from ninja import Header, Router
from ninja.responses import Status
from notifications._event_feedback_notifications import notify_event_feedback

from community._event_feedback_schemas import EventFeedbackOut, EventFeedbackSubmitOut
from community._shared import ErrorOut
from community._survey_helpers import _survey_out, survey_is_open
from community._survey_schemas import SurveyAnswersIn
from community._survey_validators import _build_survey_answers, _validate_survey_answers
from community._validation import Code, raise_validation
from community.models import EventFeedbackRequest, Survey, SurveyResponse
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
        qs = qs.select_for_update()
    try:
        return qs.get(token=token)
    except EventFeedbackRequest.DoesNotExist:
        raise_validation(Code.Survey.FEEDBACK_LINK_INVALID, status_code=404)


@router.get("/event-feedback/", response={200: EventFeedbackOut, 404: ErrorOut}, auth=None)
def get_event_feedback(request, token: str = FeedbackToken):
    feedback_request = _feedback_request_or_404(token)
    event = feedback_request.event
    survey = feedback_survey_for(event.event_type)
    return Status(
        200,
        EventFeedbackOut(
            survey=_survey_out(survey, include_questions=True) if survey else None,
            event_id=str(event.id),
            event_title=event.title,
            event_start=event.start_datetime,
            already_responded=feedback_request.responded_on is not None,
            is_open=survey is not None and survey_is_open(survey),
        ),
    )


def _open_feedback_survey(feedback_request: EventFeedbackRequest) -> Survey:
    if feedback_request.responded_on is not None:
        raise_validation(Code.Survey.FEEDBACK_ALREADY_SUBMITTED, status_code=400)
    survey = feedback_survey_for(feedback_request.event.event_type)
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
@rate_limit(key_func=lambda r: r.META.get("REMOTE_ADDR", "anon"), rate="20/h")
def submit_event_feedback(request, payload: SurveyAnswersIn, token: str = FeedbackToken):
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
        feedback_request.responded_on = timezone.localdate()
        feedback_request.save(update_fields=["responded_on"])
        mark_request_anonymized(request)
        audit_log(
            logging.INFO,
            "survey_response_submitted",
            request,
            target=AuditTarget(type=AuditTargetType.SURVEY, id=str(survey.id)),
        )
        event = feedback_request.event
        transaction.on_commit(lambda: notify_event_feedback(event))
    return Status(201, EventFeedbackSubmitOut(confirmation_message=survey.confirmation_message))
