from community.models import Event, EventRSVP, FeatureFlag, RSVPStatus, flag_enabled


def event_requires_payment_confirmation(event: Event) -> bool:
    """True when the event names a price AND offers at least one way to pay it."""
    has_price = bool(event.price.strip())
    has_payment_method = any(
        bool(value.strip()) for value in (event.venmo_link, event.cashapp_link, event.zelle_info)
    )
    return has_price and has_payment_method


def can_see_payment_details(
    event: Event, is_authed: bool, gate_flag_enabled: bool | None = None
) -> bool:
    """Payment details are wider than the other member-only links: a stranger who
    can publicly rsvp has to be able to see how to pay.

    Flag-gated: while EVENT_PAYMENT_CONFIRMATION is off, no gate exists to make
    a stranger's payment need real, so anon visibility must not widen either.
    Callers serializing a list of events should resolve the flag once and pass
    it in via gate_flag_enabled — flag_enabled() is a query, and calling it
    per-event in a loop reintroduces the N+1 this function otherwise avoids.
    """
    if gate_flag_enabled is None:
        gate_flag_enabled = flag_enabled(FeatureFlag.EVENT_PAYMENT_CONFIRMATION)
    if not gate_flag_enabled:
        return is_authed
    return is_authed or (
        event.is_public_rsvp_eligible and event_requires_payment_confirmation(event)
    )


def waitlist_promotion_needs_payment(event: Event) -> bool:
    """True when a waitlist promotion or poll-finalize seat is provisional pending payment.

    Same flag guard as requires_payment_gate — the "pay to keep your spot"
    messaging must not fire while the gate itself is disabled.
    """
    return flag_enabled(
        FeatureFlag.EVENT_PAYMENT_CONFIRMATION
    ) and event_requires_payment_confirmation(event)


def requires_payment_gate(event: Event, existing: EventRSVP | None, requested_status: str) -> bool:
    """True when this RSVP write must carry a payment confirmation.

    Checked against the *requested* status, not the post-capacity-resolution
    one: at capacity, attending downgrades to waitlisted, and that write must
    still gate — otherwise an unconfirmed row is queued and later promoted to
    attending with no gate ever having run.

    Keyed on the stamp, not the status transition: waitlist promotion seats a
    row as attending without ever passing this gate, so "already attending"
    cannot be treated as proof of payment.
    """
    if not flag_enabled(FeatureFlag.EVENT_PAYMENT_CONFIRMATION):
        return False
    if requested_status != RSVPStatus.ATTENDING:
        return False
    if not event_requires_payment_confirmation(event):
        return False
    return existing is None or existing.paid_confirmed_at is None
