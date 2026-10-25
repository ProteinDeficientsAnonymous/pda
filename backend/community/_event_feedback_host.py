from uuid import UUID

from config.auth import gated_jwt
from django.conf import settings
from ninja import Router
from ninja.responses import Status

from community._event_feedback_host_schemas import (
    EventFeedbackHostOut,
    HostFeedbackResponseOut,
    MyEventFeedbackOut,
)
from community._event_helpers import _can_edit_event
from community._shared import ErrorOut
from community._survey_helpers import _survey_question_out
from community._validation import Code, raise_validation
from community.models import Event, EventFeedbackRequest, SurveyQuestionType, SurveyResponse
from community.models.event_feedback import feedback_survey_for

router = Router()


def _response_out(response: SurveyResponse) -> HostFeedbackResponseOut:
    return HostFeedbackResponseOut(
        id=str(response.id),
        answers=response.answers,
        submitted_on=response.submitted_at.astimezone(settings.COMMUNITY_TZ).date(),
    )


@router.get(
    "/events/{event_id}/feedback/",
    response={200: EventFeedbackHostOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_event_feedback(request, event_id: UUID):
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="event_feedback")

    survey = feedback_survey_for(event.event_type)
    asked = survey.questions.exclude(field_type=SurveyQuestionType.SECTION) if survey else []
    questions = [_survey_question_out(q) for q in asked]
    # Day-only ordering with an id tiebreak so row order can't reveal submit order within a day.
    responses = sorted(
        (_response_out(r) for r in SurveyResponse.objects.filter(event=event)),
        key=lambda r: (-r.submitted_on.toordinal(), r.id),
    )
    return Status(200, EventFeedbackHostOut(questions=questions, responses=responses))


@router.get(
    "/events/{event_id}/my-feedback/",
    response={200: MyEventFeedbackOut},
    auth=gated_jwt,
)
def get_my_event_feedback(request, event_id: UUID):
    feedback_request = EventFeedbackRequest.objects.filter(
        event_id=event_id, user=request.auth, responded_on__isnull=True
    ).first()
    return Status(
        200, MyEventFeedbackOut(token=feedback_request.token if feedback_request else None)
    )
