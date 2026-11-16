from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from community.field_limits import FieldLimit
from community.models import ReserveEntry


class ReserveEntryOut(BaseModel):
    id: str
    label: str
    occurred_on: date
    collected: Decimal
    paid_out: Decimal
    facilitator_drinks: Decimal
    left_over: Decimal


class ReserveOut(BaseModel):
    entries: list[ReserveEntryOut]
    updated_at: datetime | None


def entry_out(entry: ReserveEntry) -> ReserveEntryOut:
    return ReserveEntryOut(
        id=str(entry.id),
        label=entry.label,
        occurred_on=entry.occurred_on,
        collected=entry.collected,
        paid_out=entry.paid_out,
        facilitator_drinks=entry.facilitator_drinks,
        left_over=entry.left_over,
    )


Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class ReserveEntryIn(BaseModel):
    label: str = Field(min_length=1, max_length=FieldLimit.TITLE)
    occurred_on: date
    collected: Money = Decimal("0")
    paid_out: Money = Decimal("0")
    facilitator_drinks: Money = Decimal("0")


class ReserveEntryPatchIn(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=FieldLimit.TITLE)
    occurred_on: date | None = None
    collected: Money | None = None
    paid_out: Money | None = None
    facilitator_drinks: Money | None = None
