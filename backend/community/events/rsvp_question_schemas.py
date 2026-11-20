from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, WithJsonSchema, field_validator

from community.field_limits import FieldLimit
from community.models import RSVP_CHOICE_TYPES
from community.validation import Code, raise_validation

RsvpQuestionFieldType = Literal["textarea", "select", "checkbox"]
RsvpQuestionOption = Annotated[str, Field(max_length=FieldLimit.OPTION_TEXT)]
RsvpTextAnswer = Annotated[
    str, WithJsonSchema({"type": "string", "maxLength": FieldLimit.DESCRIPTION})
]
RsvpAnswer = RsvpTextAnswer | list[RsvpQuestionOption]


class EventRsvpQuestionOut(BaseModel):
    id: str
    label: str
    field_type: RsvpQuestionFieldType
    options: list[str] = []
    required: bool
    display_order: int


class EventRsvpQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: RsvpQuestionFieldType
    options: list[RsvpQuestionOption] = []
    required: bool = False

    @field_validator("label")
    @classmethod
    def label_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("label required")
        return trimmed

    @field_validator("options")
    @classmethod
    def trim_options(cls, value: list[str]) -> list[str]:
        trimmed = [o.strip() for o in value if o.strip()]
        if any(len(option) > FieldLimit.OPTION_TEXT for option in trimmed):
            raise ValueError(f"options must be {FieldLimit.OPTION_TEXT} characters or fewer")
        return trimmed


class EventRsvpQuestionSyncIn(EventRsvpQuestionIn):
    id: UUID | None = None


class EventRsvpQuestionExpectedIn(EventRsvpQuestionIn):
    id: UUID


class EventRsvpQuestionSyncPayload(BaseModel):
    expected: list[EventRsvpQuestionExpectedIn]
    questions: list[EventRsvpQuestionSyncIn]


def validate_event_rsvp_question(payload: EventRsvpQuestionIn) -> None:
    if payload.field_type in RSVP_CHOICE_TYPES and not payload.options:
        raise_validation(
            Code.Event.RSVP_QUESTION_OPTIONS_REQUIRED, field="options", status_code=400
        )
