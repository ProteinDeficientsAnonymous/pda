"""Pydantic schemas for survey endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from community._field_limits import FieldLimit
from community.models import SurveyQuestionType, SurveyVisibility


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


class VoterOut(BaseModel):
    user_id: str
    name: str
    photo_url: str


class PollResultsOut(BaseModel):
    question_id: str
    tallies: dict[str, dict[str, int]]  # option -> {"yes": N, "maybe": M}
    voters: dict[str, list[VoterOut]] = {}
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
    my_answers: dict | None = None


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
    title: str = Field(max_length=FieldLimit.TITLE)
    description: str = Field(default="", max_length=FieldLimit.DESCRIPTION)
    slug: str = Field(max_length=FieldLimit.SLUG)
    visibility: str = Field(default=SurveyVisibility.PUBLIC, max_length=FieldLimit.CHOICE)
    is_active: bool = True
    one_response_per_user: bool = False
    linked_event_id: str | None = None


class SurveyPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    description: str | None = Field(default=None, max_length=FieldLimit.DESCRIPTION)
    slug: str | None = Field(default=None, max_length=FieldLimit.SLUG)
    visibility: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    is_active: bool | None = None
    one_response_per_user: bool | None = None
    linked_event_id: str | None = None


class FinalizePollIn(BaseModel):
    winning_datetime: datetime


class SurveyQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: str = Field(default=SurveyQuestionType.TEXT, max_length=FieldLimit.CHOICE)
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


# str for standard question types (text, select, number, etc.)
# dict[str, str] for availability answers (option -> "yes"|"maybe")
TextAnswer = str
AvailabilityAnswer = dict[str, str]


class SurveyAnswersIn(BaseModel):
    answers: dict[str, TextAnswer | AvailabilityAnswer]

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(
        cls, v: dict[str, TextAnswer | AvailabilityAnswer]
    ) -> dict[str, TextAnswer | AvailabilityAnswer]:
        for key, answer in v.items():
            if isinstance(answer, str) and len(answer) > FieldLimit.DESCRIPTION:
                raise ValueError(
                    f"Answer for question {key} exceeds {FieldLimit.DESCRIPTION} characters."
                )
        return v
