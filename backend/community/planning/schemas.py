from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from community.models import AssignmentStatus, BiannualInterest, PlanningSlotKind


class PlanningYearOut(BaseModel):
    id: str
    year: int


class PlanningSlotOut(BaseModel):
    id: str
    label: str
    month: int
    kind: PlanningSlotKind
    order: int
    event_id: str | None
    event_slug: str | None
    event_status: str | None


class PlanningYearIn(BaseModel):
    year: int = Field(ge=2020, le=2100)


class PlanningSlotIn(BaseModel):
    label: str = Field(max_length=100)
    month: int = Field(ge=1, le=12)
    kind: PlanningSlotKind


class PlanningSlotPatchIn(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    month: int | None = Field(default=None, ge=1, le=12)
    kind: PlanningSlotKind | None = None


class AvailabilityOut(BaseModel):
    submitted: bool
    biannual_interest: str | None
    monthly_count: int
    slot_ids: list[str]
    updated_at: datetime | None


class AvailabilityIn(BaseModel):
    slot_ids: list[UUID] = Field(max_length=50)
    biannual_interest: BiannualInterest
    monthly_count: int = Field(ge=0, le=12)


class ProposeIn(BaseModel):
    user_id: UUID


class AssignmentOut(BaseModel):
    id: str
    slot_id: str
    user_id: str
    status: AssignmentStatus
    proposed_at: datetime
    responded_at: datetime | None
