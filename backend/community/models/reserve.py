import uuid
from decimal import Decimal

from django.db import models

from community.field_limits import FieldLimit


def _money(**kwargs) -> models.DecimalField:
    return models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"), **kwargs)


class ReserveEntry(models.Model):
    """One line of the public reserve breakdown: an event, donation, or cost."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=FieldLimit.TITLE)
    occurred_on = models.DateField()
    collected = _money()
    paid_out = _money()
    facilitator_drinks = _money()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        ordering = ["occurred_on", "created_at"]

    def __str__(self) -> str:
        return f"ReserveEntry({self.occurred_on} {self.label})"

    @property
    def left_over(self) -> Decimal:
        return self.collected - self.paid_out - self.facilitator_drinks
