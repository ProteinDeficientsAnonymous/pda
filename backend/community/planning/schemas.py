from pydantic import BaseModel, Field

from community.models import PlanningSlotKind


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
