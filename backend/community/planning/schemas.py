from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

from community.models import AssignmentStatus, BiannualInterest, EventStatus, PlanningSlotKind


class PlanningYearOut(BaseModel):
    id: str
    year: int
    availability_opened_at: datetime | None


class PlanningSlotOut(BaseModel):
    id: str
    label: str
    month: int
    kind: PlanningSlotKind
    order: int
    event_id: str | None
    event_slug: str | None
    event_status: EventStatus | None


class PlanningYearIn(BaseModel):
    year: int = Field(ge=2020, le=2100)


def _label_not_blank(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("label required")
    return trimmed


SlotLabel = Annotated[str, Field(max_length=100), AfterValidator(_label_not_blank)]


class PlanningSlotIn(BaseModel):
    label: SlotLabel
    month: int = Field(ge=1, le=12)
    kind: PlanningSlotKind


class PlanningSlotPatchIn(BaseModel):
    label: SlotLabel | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    kind: PlanningSlotKind | None = None


class AvailabilityOut(BaseModel):
    submitted: bool
    biannual_interest: BiannualInterest | None
    monthly_count: int
    slot_ids: list[str]
    updated_at: datetime | None


class AvailabilityIn(BaseModel):
    slot_ids: list[UUID] = Field(max_length=50)
    biannual_interest: BiannualInterest
    monthly_count: int = Field(ge=0, le=12)


class LinkEventIn(BaseModel):
    event_id: UUID


class ProposeIn(BaseModel):
    user_id: UUID


class AssignmentOut(BaseModel):
    id: str
    slot_id: str
    user_id: str
    status: AssignmentStatus
    proposed_at: datetime
    responded_at: datetime | None


class ProposalsSentOut(BaseModel):
    planners_notified: int
    proposals_sent: int


class PlannerColumnOut(BaseModel):
    user_id: str
    name: str
    is_planner: bool
    has_email: bool
    submitted: bool
    biannual_interest: BiannualInterest | None
    monthly_count: int
    available_slot_ids: list[str]


class GridOut(BaseModel):
    slots: list[PlanningSlotOut]
    planners: list[PlannerColumnOut]
    assignments: list[AssignmentOut]


class TeammateOut(BaseModel):
    name: str
    status: AssignmentStatus


class MySlotOut(BaseModel):
    assignment_id: str
    status: AssignmentStatus
    year: int
    slot: PlanningSlotOut
    teammates: list[TeammateOut]
