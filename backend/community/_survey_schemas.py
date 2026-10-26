"""Pydantic schemas for survey endpoints."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from community._field_limits import FieldLimit
from community.models import EventType, ShowIfOperator, SurveyQuestionType, SurveyVisibility

SCALE_END_LABELS = 2


def scale_end_labels(options: list[str]) -> list[str]:
    """return(list): [low, high] labels for a 1-5 scale, or [] when both are blank."""
    if len(options) > SCALE_END_LABELS:
        raise ValueError("scale questions take at most 2 end labels: low, high")
    labels = [label.strip() for label in options]
    labels += [""] * (SCALE_END_LABELS - len(labels))
    return labels if any(labels) else []


class ShowIfIn(BaseModel):
    question_id: UUID
    operator: ShowIfOperator = ShowIfOperator.EQUALS
    value: str = Field(max_length=FieldLimit.SHORT_TEXT)


class ShowIfOut(BaseModel):
    question_id: str
    operator: str
    value: str


class SurveyQuestionOut(BaseModel):
    id: str
    label: str
    field_type: SurveyQuestionType
    options: list[str] = []
    description: str = ""
    required: bool
    display_order: int
    show_if: ShowIfOut | None = None


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


class QuestionSummaryOut(BaseModel):
    question_id: str
    field_type: SurveyQuestionType
    counts: dict[str, int]  # option (or "yes"/"no", or "1".."5") -> count
    answered: int
    mean: float | None = None


class SurveyOut(BaseModel):
    id: str
    title: str
    description: str
    slug: str
    visibility: str
    is_active: bool
    one_response_per_user: bool = False
    anonymous: bool = False
    confirmation_message: str = ""
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_responses: int | None = None
    linked_event_id: str | None = None
    feedback_event_type: str = ""
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
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_responses: int | None = None
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
    anonymous: bool = False
    confirmation_message: str = Field(default="", max_length=FieldLimit.SURVEY_CONFIRMATION_MESSAGE)
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_responses: int | None = Field(default=None, ge=1)
    linked_event_id: str | None = None
    feedback_event_type: Literal[EventType.OFFICIAL, EventType.CLUB, ""] = ""


class SurveyPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    description: str | None = Field(default=None, max_length=FieldLimit.DESCRIPTION)
    slug: str | None = Field(default=None, max_length=FieldLimit.SLUG)
    visibility: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    is_active: bool | None = None
    one_response_per_user: bool | None = None
    anonymous: bool | None = None
    confirmation_message: str | None = Field(
        default=None, max_length=FieldLimit.SURVEY_CONFIRMATION_MESSAGE
    )
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    max_responses: int | None = Field(default=None, ge=1)
    linked_event_id: str | None = None
    feedback_event_type: Literal[EventType.OFFICIAL, EventType.CLUB, ""] | None = None


class FinalizePollIn(BaseModel):
    winning_datetime: datetime


class SurveyQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: SurveyQuestionType = SurveyQuestionType.TEXT
    options: list[str] = []
    description: str = Field(default="", max_length=FieldLimit.DESCRIPTION)
    required: bool = False
    show_if: ShowIfIn | None = None

    @model_validator(mode="after")
    def _section_takes_no_answer(self) -> Self:
        if self.field_type == SurveyQuestionType.SECTION:
            self.options, self.required = [], False
        else:
            self.description = ""
        if self.field_type == SurveyQuestionType.SCALE:
            self.options = scale_end_labels(self.options)
        return self


class SurveyQuestionOrderIn(BaseModel):
    question_ids: list[str]


class SurveyResponseOut(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    answers: dict
    submitted_at: datetime
    event_id: str | None = None
    event_title: str | None = None
    event_start: datetime | None = None


class SurveySubmitOut(SurveyResponseOut):
    response_token: str | None = None


# str for standard question types (text, select, number, etc.)
# list[str] for checkbox answers (ticked options)
# dict[str, str] for availability answers (option -> "yes"|"maybe")
TextAnswer = str
ChoiceListAnswer = list[str]
AvailabilityAnswer = dict[str, str]
SurveyAnswer = TextAnswer | ChoiceListAnswer | AvailabilityAnswer


class SurveyAnswersIn(BaseModel):
    answers: dict[str, SurveyAnswer]

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(cls, v: dict[str, SurveyAnswer]) -> dict[str, SurveyAnswer]:
        for key, answer in v.items():
            text = "".join(answer) if isinstance(answer, list) else answer
            if isinstance(text, str) and len(text) > FieldLimit.DESCRIPTION:
                raise ValueError(
                    f"Answer for question {key} exceeds {FieldLimit.DESCRIPTION} characters."
                )
        return v
