from datetime import datetime

from pydantic import BaseModel

from community._survey_schemas import SurveyOut


class EventFeedbackOut(BaseModel):
    survey: SurveyOut | None
    event_id: str
    event_title: str
    event_start: datetime | None
    already_responded: bool
    is_open: bool


class EventFeedbackSubmitOut(BaseModel):
    confirmation_message: str
