from pydantic import BaseModel, Field


class PlanningYearOut(BaseModel):
    id: str
    year: int


class PlanningYearIn(BaseModel):
    year: int = Field(ge=2020, le=2100)
