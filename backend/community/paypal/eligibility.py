from community.models import EventType
from community.validation import Code, raise_validation


def ensure_paypal_allowed(accept_paypal: bool | None, event_type: str) -> None:
    # Card payments land in the collective's paypal account, so only official events take them.
    if accept_paypal and event_type != EventType.OFFICIAL:
        raise_validation(Code.Event.PAYPAL_OFFICIAL_ONLY, field="accept_paypal")
