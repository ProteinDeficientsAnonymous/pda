from datetime import date

from pydantic import BaseModel

from community._survey_schemas import SurveyQuestionOut


class HostFeedbackResponseOut(BaseModel):
    id: str
    answers: dict
    submitted_on: date


class EventFeedbackHostOut(BaseModel):
    questions: list[SurveyQuestionOut]
    responses: list[HostFeedbackResponseOut]
