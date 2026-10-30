"""Pydantic schemas for EventPoll endpoints."""

from datetime import datetime

from pydantic import BaseModel


class VoterOut(BaseModel):
    user_id: str
    name: str
    photo_url: str


class EventPollOptionOut(BaseModel):
    id: str
    datetime: datetime
    display_order: int
    yes_count: int
    maybe_count: int
    no_count: int = 0
    yes_voters: list[VoterOut] = []
    maybe_voters: list[VoterOut] = []
    no_voters: list[VoterOut] = []


class EventPollOut(BaseModel):
    id: str
    event_id: str
    is_active: bool
    options: list[EventPollOptionOut] = []
    winning_option_id: str | None = None
    winning_datetime: datetime | None = None
    finalized_by_id: str | None = None
    finalized_at: datetime | None = None
    my_votes: dict[str, str] = {}  # option_id -> "yes" | "maybe" | "no"


class EventPollIn(BaseModel):
    options: list[datetime]


class PollOptionIn(BaseModel):
    datetime: datetime


class EventPollVoteIn(BaseModel):
    votes: dict[str, str]  # option_id -> "yes" | "maybe" | "no"


class EventPollFinalizeIn(BaseModel):
    winning_option_id: str
