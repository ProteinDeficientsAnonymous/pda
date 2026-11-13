import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.utils import timezone

from community.models.choices import (
    AssignmentStatus,
    BiannualInterest,
    EventStatus,
    PlanningSlotKind,
)

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
        assignments: "Manager[SlotAssignment]"

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


class PlanningAvailability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning_year = models.ForeignKey(
        PlanningYear, on_delete=models.CASCADE, related_name="availabilities"
    )
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="planning_availabilities"
    )
    biannual_interest = models.CharField(max_length=10, choices=BiannualInterest.choices)
    monthly_count = models.PositiveSmallIntegerField(default=0)
    available_slots = models.ManyToManyField(PlanningSlot, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    if TYPE_CHECKING:
        user_id: uuid.UUID

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["planning_year", "user"], name="unique_planning_availability"
            ),
        ]

    def __str__(self) -> str:
        return f"PlanningAvailability({self.planning_year}, {self.user_id})"


class SlotAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot = models.ForeignKey(PlanningSlot, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="slot_assignments"
    )
    status = models.CharField(
        max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.PROPOSED
    )
    proposed_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    proposed_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.PositiveSmallIntegerField(default=0)
    upcoming_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        slot_id: uuid.UUID
        user_id: uuid.UUID

    class Meta:
        app_label = "community"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["slot", "user"], name="unique_slot_assignment"),
        ]

    def propose(self, by) -> None:
        with transaction.atomic():
            self.status = AssignmentStatus.PROPOSED
            self.proposed_by = by
            self.proposed_at = timezone.now()
            self.responded_at = None
            self.last_reminded_at = None
            self.reminder_count = 0
            self.upcoming_notified_at = None
            self.save()

    def _respond(self, status: AssignmentStatus) -> None:
        with transaction.atomic():
            self.status = status
            self.responded_at = timezone.now()
            self.save(update_fields=["status", "responded_at"])

    def commit(self) -> None:
        self._respond(AssignmentStatus.COMMITTED)

    def decline(self) -> None:
        self._respond(AssignmentStatus.DECLINED)

    def withdraw(self) -> None:
        self._respond(AssignmentStatus.WITHDRAWN)

    def __str__(self) -> str:
        return f"SlotAssignment({self.slot}, {self.user_id}, {self.status})"
