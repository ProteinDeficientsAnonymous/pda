from decimal import Decimal
from unittest.mock import MagicMock, patch

from community.models import EventRSVP, RSVPStatus
from users.models import User

from tests._payment_helpers import create_eligible_event


def mock_paypal(payload: dict):
    """Patch PayPal's HTTP calls: the access token, then `payload`."""
    responses = [{"access_token": "token"}, payload]
    return patch(
        "community.paypal._client.httpx.post",
        side_effect=[MagicMock(**{"json.return_value": r}) for r in responses],
    )


def create_paypal_rsvp(user: User) -> EventRSVP:
    event = create_eligible_event(created_by=user, accept_paypal=True, price=Decimal("10"))
    return EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.WAITLISTED)


def completed_capture(rsvp: EventRSVP, status: str = "COMPLETED") -> dict:
    return {"id": "CAP-1", "status": status, "custom_id": str(rsvp.pk)}
