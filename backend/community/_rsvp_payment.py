from community.models import Event, EventRSVP, FeatureFlag, RSVPStatus, flag_enabled


def event_requires_payment_confirmation(event: Event) -> bool:
    has_price = bool(event.price.strip())
    has_payment_method = any(
        bool(value.strip()) for value in (event.venmo_link, event.cashapp_link, event.zelle_info)
    )
    return has_price and has_payment_method


def can_see_payment_details(event: Event, is_authed: bool) -> bool:
    return is_authed or (
        event.is_public_rsvp_eligible and event_requires_payment_confirmation(event)
    )


def payment_enforced_for_event(event: Event) -> bool:
    return flag_enabled(
        FeatureFlag.EVENT_PAYMENT_CONFIRMATION
    ) and event_requires_payment_confirmation(event)


def requires_payment_gate(event: Event, existing: EventRSVP | None, requested_status: str) -> bool:
    # Checked against the requested status, not the post-capacity one: at
    # capacity attending resolves to waitlisted, which must still gate.
    if requested_status not in (RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED):
        return False
    if not payment_enforced_for_event(event):
        return False
    return existing is None or existing.paid_confirmed_at is None
