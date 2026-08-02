from community.models import Event, EventRSVP, FeatureFlag, RSVPStatus, flag_enabled


def event_requires_payment_confirmation(event: Event) -> bool:
    """True when the event names a price AND offers at least one way to pay it."""
    has_price = bool(event.price.strip())
    has_payment_method = any(
        bool(value.strip()) for value in (event.venmo_link, event.cashapp_link, event.zelle_info)
    )
    return has_price and has_payment_method


def can_see_payment_details(event: Event, is_authed: bool) -> bool:
    """Payment details are wider than the other member-only links: a stranger who
    can publicly rsvp has to be able to see how to pay."""
    return is_authed or event.is_public_rsvp_eligible


def requires_payment_gate(event: Event, existing: EventRSVP | None, final_status: str) -> bool:
    """True when this RSVP write must carry a payment confirmation.

    Keyed on the stamp, not the status transition: waitlist promotion seats a
    row as attending without ever passing this gate, so "already attending"
    cannot be treated as proof of payment.
    """
    if not flag_enabled(FeatureFlag.EVENT_PAYMENT_CONFIRMATION):
        return False
    if final_status != RSVPStatus.ATTENDING:
        return False
    if not event_requires_payment_confirmation(event):
        return False
    return existing is None or existing.paid_confirmed_at is None
