from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, WithJsonSchema, field_validator, model_validator

from community.field_limits import FieldLimit
from community.models import RSVP_CHOICE_TYPES
from community.validation import Code, raise_validation

RsvpQuestionFieldType = Literal["textarea", "select", "checkbox"]
RsvpQuestionOption = Annotated[str, Field(max_length=FieldLimit.OPTION_TEXT)]
MAX_OPTION_PRICE_CENTS = 1_000_000
RsvpOptionPrice = Annotated[int, Field(ge=0, le=MAX_OPTION_PRICE_CENTS)]
RsvpTextAnswer = Annotated[
    str, WithJsonSchema({"type": "string", "maxLength": FieldLimit.DESCRIPTION})
]
RsvpAnswer = RsvpTextAnswer | list[RsvpQuestionOption]


class EventRsvpQuestionOut(BaseModel):
    id: str
    label: str
    field_type: RsvpQuestionFieldType
    options: list[str] = []
    option_prices: list[int] = []
    required: bool
    display_order: int


class EventRsvpQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: RsvpQuestionFieldType
    options: list[RsvpQuestionOption] = []
    option_prices: list[RsvpOptionPrice] = Field(
        default_factory=list, description="Cents per option, parallel to options; empty = unpriced."
    )
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

    @model_validator(mode="after")
    def prices_match_options(self):
        if not self.option_prices:
            return self
        if self.field_type not in RSVP_CHOICE_TYPES:
            raise ValueError("only select and checkbox questions can be priced")
        if len(self.option_prices) != len(self.options):
            raise ValueError("option_prices must have one price per option")
        return self


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
