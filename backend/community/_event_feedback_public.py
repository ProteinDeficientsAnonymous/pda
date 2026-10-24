from ninja import Router
from ninja.responses import Status

from community._event_feedback_schemas import EventFeedbackOut
from community._shared import ErrorOut
from community._survey_helpers import _survey_out, survey_is_open
from community._survey_schemas import SurveyOut
from community._validation import Code, raise_validation
from community.models import EventFeedbackRequest, Survey
from community.models.event_feedback import feedback_survey_for

router = Router()


def _feedback_request_or_404(token: str, *, for_update: bool = False) -> EventFeedbackRequest:
    qs = EventFeedbackRequest.objects.select_related("event")
    if for_update:
        qs = qs.select_for_update()
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


@router.get("/feedback/{token}/", response={200: EventFeedbackOut, 404: ErrorOut}, auth=None)
def get_event_feedback(request, token: str):
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
            is_open=survey is not None and survey_is_open(survey),
        ),
    )
