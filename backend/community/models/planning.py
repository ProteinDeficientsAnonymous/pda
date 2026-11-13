import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.db import models, transaction

from community.models.choices import EventStatus, PlanningSlotKind

if TYPE_CHECKING:
    from django.db.models import Manager

    from community.models.event import Event

_MONTHS = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)  # fmt: skip
_BIANNUALS = (("june anniversary", 6), ("dec holiday", 12))


class PlanningYear(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.PositiveSmallIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        slots: "Manager[PlanningSlot]"

    class Meta:
        app_label = "community"
        ordering = ["-year"]

    @classmethod
    def create_with_default_slots(cls, year: int) -> "PlanningYear":
        defaults = [(label, i, PlanningSlotKind.MONTHLY) for i, label in enumerate(_MONTHS, 1)]
        defaults += [(label, month, PlanningSlotKind.BIANNUAL) for label, month in _BIANNUALS]
        with transaction.atomic():
            planning_year = cls.objects.create(year=year)
            PlanningSlot.objects.bulk_create(
                PlanningSlot(
                    planning_year=planning_year, label=label, month=month, kind=kind, order=order
                )
                for order, (label, month, kind) in enumerate(defaults, 1)
            )
        return planning_year

    def __str__(self) -> str:
        return str(self.year)


class PlanningSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning_year = models.ForeignKey(PlanningYear, on_delete=models.CASCADE, related_name="slots")
    label = models.CharField(max_length=100)
    month = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=20, choices=PlanningSlotKind.choices)
    event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="planning_slots",
    )
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        planning_year_id: uuid.UUID
        event_id: uuid.UUID | None

    class Meta:
        app_label = "community"
        ordering = ["order"]

    @property
    def live_event(self) -> "Event | None":
        if self.event is None or self.event.status == EventStatus.DELETED:
            return None
        return self.event

    def month_start(self) -> date:
        return date(self.planning_year.year, self.month, 1)

    def __str__(self) -> str:
        return f"{self.planning_year} {self.label}"
