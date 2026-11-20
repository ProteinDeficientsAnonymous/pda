from decimal import Decimal

import httpx
from django.conf import settings

_API_BASE = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}
_TIMEOUT = 10.0


def paypal_configured() -> bool:
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def _url(path: str) -> str:
    return f"{_API_BASE[settings.PAYPAL_ENV]}{path}"


def _access_token() -> str:
    resp = httpx.post(
        _url("/v1/oauth2/token"),
        data={"grant_type": "client_credentials"},
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def post(path: str, payload: dict) -> dict:
    """POST to the PayPal REST API; raises httpx.HTTPError on any failure."""
    resp = httpx.post(
        _url(path),
        json=payload,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def create_order(*, rsvp_id: str, amount: Decimal, description: str) -> str:
    """return(str): the new PayPal order id."""
    order = post(
        "/v2/checkout/orders",
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "custom_id": rsvp_id,
                    "description": description[:127],
                    "amount": {"currency_code": "USD", "value": str(amount)},
                }
            ],
        },
    )
    return order["id"]
