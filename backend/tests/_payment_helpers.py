"""Shared factories for the payment-confirmation tests (Issue 1045)."""

from datetime import timedelta

from community.models import (
    Event,
    EventStatus,
    EventType,
    FeatureFlag,
    PageVisibility,
)
from django.utils import timezone

from tests.conftest import set_flag

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


def set_payment_flag(enabled: bool = True) -> None:
    set_flag(FLAG, enabled)


def _paid_defaults(**overrides) -> dict:
    # Real datetimes, not future_iso() strings — is_public_rsvp_eligible reaches
    # through is_past, which compares against timezone.now().
    start = timezone.now() + timedelta(days=10)
    base = {
        "title": "Paid Event",
        "start_datetime": start,
        "end_datetime": start + timedelta(hours=2),
        "rsvp_enabled": True,
        "status": EventStatus.ACTIVE,
        "visibility": PageVisibility.PUBLIC,
        "price": "$10",
        "venmo_link": "https://venmo.com/u/host",
    }
    base.update(overrides)
    return base


def build_paid_event(**overrides) -> Event:
    """Unsaved — for predicates that only read fields."""
    return Event(**_paid_defaults(**overrides))


def build_eligible_event(**overrides) -> Event:
    """Unsaved, and satisfies Event.is_public_rsvp_eligible."""
    return build_paid_event(**{"event_type": EventType.OFFICIAL, **overrides})


def create_paid_event(**overrides) -> Event:
    return Event.objects.create(**_paid_defaults(**overrides))


def create_eligible_event(**overrides) -> Event:
    return create_paid_event(**{"event_type": EventType.OFFICIAL, **overrides})
