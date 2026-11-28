from datetime import date

import pytest
from community.models import (
    AssignmentStatus,
    EventStatus,
    PlanningChecklistItem,
    PlanningSlotKind,
    PlanningYear,
    SlotAssignment,
    SlotChecklistTick,
)
from django.db import IntegrityError

from tests._events import make_event
from tests._users import make_user

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]  # fmt: skip


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


@pytest.mark.django_db
class TestSlotAssignment:
    def test_repropose_resets_counters(self, year):
        coordinator, planner = make_user(), make_user()
        slot = year.slots.first()
        assert slot is not None
        assignment = SlotAssignment(slot=slot, user=planner)
        assignment.propose(coordinator)
        assignment.decline()
        assignment.reminder_count = 3
        assignment.save()
        assignment.propose(coordinator)
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.PROPOSED
        assert assignment.reminder_count == 0
        assert assignment.responded_at is None
        assert assignment.last_reminded_at is None

    def test_commit_stamps_response(self, year):
        slot = year.slots.first()
        assert slot is not None
        assignment = SlotAssignment(slot=slot, user=make_user())
        assignment.propose(make_user())
        assignment.commit()
        assignment.refresh_from_db()
        assert assignment.status == AssignmentStatus.COMMITTED
        assert assignment.responded_at is not None

    def test_one_assignment_per_slot_and_user(self, year):
        slot, user = year.slots.first(), make_user()
        SlotAssignment.objects.create(slot=slot, user=user)
        with pytest.raises(IntegrityError):
            SlotAssignment.objects.create(slot=slot, user=user)


@pytest.mark.django_db
class TestPlanningChecklist:
    def test_seeded_in_order(self):
        items = list(PlanningChecklistItem.objects.all())
        assert items[0].text == "secure venue"
        assert items[-1].text.startswith("after the meetup")
        assert "opt out" in items[4].detail

    def test_one_tick_per_slot_item(self, year):
        slot = year.slots.get(label="march")
        item = PlanningChecklistItem.objects.first()
        SlotChecklistTick.objects.create(slot=slot, item=item)
        with pytest.raises(IntegrityError):
            SlotChecklistTick.objects.create(slot=slot, item=item)

    def test_deleting_item_drops_ticks(self, year):
        item = PlanningChecklistItem.objects.create(text="book a room", order=99)
        SlotChecklistTick.objects.create(slot=year.slots.first(), item=item, done_by=make_user())
        item.delete()
        assert not SlotChecklistTick.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("year_number", "month", "due"),
    [
        (2027, 1, date(2026, 12, 14)),
        (2027, 2, date(2026, 12, 31)),
        (2027, 3, date(2027, 1, 31)),
        (2027, 4, date(2027, 2, 28)),
        (2028, 1, date(2027, 11, 30)),
    ],
)
def test_event_due_is_day_before_its_announcement(year_number, month, due):
    slot = PlanningYear.create_with_default_slots(year_number).slots.get(order=month)
    assert slot.event_due() == due
