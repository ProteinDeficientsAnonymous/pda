from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import MagicMock, patch

from community.models import EventRSVP, RSVPStatus
from users.models import User

from tests._payment_helpers import create_eligible_event


def _response(payload: dict) -> MagicMock:
    return MagicMock(**{"json.return_value": payload})


@contextmanager
def mock_paypal(payload: dict, order: dict | None = None):
    """Patch PayPal's HTTP calls: a token before each call, `order` for a GET, then `payload`."""
    token = {"access_token": "token"}
    posts = [token, token, payload] if order else [token, payload]
    with (
        patch("community.paypal._client.httpx.get", return_value=_response(order or {})),
        patch(
            "community.paypal._client.httpx.post", side_effect=[_response(r) for r in posts]
        ) as post,
    ):
        yield post


def create_paypal_rsvp(user: User) -> EventRSVP:
    event = create_eligible_event(created_by=user, accept_paypal=True, price=Decimal("10"))
    return EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.WAITLISTED)


def completed_capture(rsvp: EventRSVP, status: str = "COMPLETED", value: str = "10.87") -> dict:
    return {
        "id": "CAP-1",
        "status": status,
        "custom_id": str(rsvp.pk),
        "amount": {"currency_code": "USD", "value": value},
    }


def approved_order(rsvp: EventRSVP, value: str = "10.87") -> dict:
    unit = {"custom_id": str(rsvp.pk), "amount": {"currency_code": "USD", "value": value}}
    return {"status": "APPROVED", "purchase_units": [unit]}
