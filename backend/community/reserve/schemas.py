from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

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
