from community.models import Event, EventRSVP, FeatureFlag, RSVPStatus, flag_enabled


def event_requires_payment_confirmation(event: Event) -> bool:
    """True when the event names a price AND offers at least one way to pay it."""
    has_price = bool(event.price.strip())
    has_payment_method = any(
        bool(value.strip()) for value in (event.venmo_link, event.cashapp_link, event.zelle_info)
    )
    return has_price and has_payment_method


def requires_payment_gate(event: Event, existing: EventRSVP | None, final_status: str) -> bool:
    """True when this RSVP write must carry a payment confirmation.

    Fires only on a transition *into* attending, so an already-attending member
    toggling a +1 or saving a comment is never re-prompted.
    """
    if not flag_enabled(FeatureFlag.EVENT_PAYMENT_CONFIRMATION):
        return False
    if final_status != RSVPStatus.ATTENDING:
        return False
    if not event_requires_payment_confirmation(event):
        return False
    if existing is not None and existing.paid_confirmed_at is not None:
        return False
    return existing is None or existing.status != RSVPStatus.ATTENDING
