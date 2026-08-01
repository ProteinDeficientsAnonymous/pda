"""Pydantic schemas for event RSVP questions."""

from pydantic import BaseModel, Field, field_validator

from community._field_limits import FieldLimit
from community.models import EventRsvpQuestionType


class EventRsvpQuestionOut(BaseModel):
    id: str
    label: str
    field_type: str
    options: list[str] = []
    required: bool
    display_order: int


class EventRsvpQuestionIn(BaseModel):
    label: str = Field(max_length=FieldLimit.SHORT_TEXT)
    field_type: EventRsvpQuestionType
    options: list[str] = []
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
        return [o.strip() for o in value if o.strip()]
