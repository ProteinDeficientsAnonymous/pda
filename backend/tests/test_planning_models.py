import pytest
from community.models import (
    EventStatus,
    PlanningSlotKind,
    PlanningYear,
)
from django.db import IntegrityError

from tests._events import make_event

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]  # fmt: skip


@pytest.fixture
def year(db) -> PlanningYear:
    return PlanningYear.create_with_default_slots(2027)


@pytest.mark.django_db
class TestPlanningYear:
    def test_default_slots(self, year):
        slots = list(year.slots.all())
        assert [s.label for s in slots] == [*MONTHS, "june anniversary", "dec holiday"]
        assert [s.month for s in slots[12:]] == [6, 12]
        assert {s.kind for s in slots[12:]} == {PlanningSlotKind.BIANNUAL}
        assert {s.kind for s in slots[:12]} == {PlanningSlotKind.MONTHLY}

    def test_year_unique(self, year):
        with pytest.raises(IntegrityError):
            PlanningYear.objects.create(year=2027)


@pytest.mark.django_db
class TestPlanningSlot:
    def test_live_event_ignores_deleted(self, year):
        slot = year.slots.get(label="march")
        slot.event = make_event(status=EventStatus.DELETED)
        assert slot.live_event is None
        slot.event.status = EventStatus.DRAFT
        assert slot.live_event == slot.event

    def test_month_start(self, year):
        assert str(year.slots.get(label="march").month_start()) == "2027-03-01"
