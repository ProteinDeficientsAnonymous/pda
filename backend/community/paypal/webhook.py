import json
import logging

import httpx
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from ninja import Router
from ninja.responses import Status

from community.paypal._capture import record_capture
from community.paypal._client import paypal_configured, post
from community.shared import ErrorOut

logger = logging.getLogger("pda")

router = Router()

CAPTURE_COMPLETED_EVENT = "PAYMENT.CAPTURE.COMPLETED"
MAX_WEBHOOK_BYTES = 64 * 1024
VERIFY_PATH = "/v1/notifications/verify-webhook-signature"
_SIGNATURE_HEADERS = {
    "auth_algo": "HTTP_PAYPAL_AUTH_ALGO",
    "cert_url": "HTTP_PAYPAL_CERT_URL",
    "transmission_id": "HTTP_PAYPAL_TRANSMISSION_ID",
    "transmission_sig": "HTTP_PAYPAL_TRANSMISSION_SIG",
    "transmission_time": "HTTP_PAYPAL_TRANSMISSION_TIME",
}


def _signature_verified(request, raw_event: str) -> bool:
    fields = {name: request.META.get(header, "") for name, header in _SIGNATURE_HEADERS.items()}
    fields["webhook_id"] = settings.PAYPAL_WEBHOOK_ID
    # Splice the raw body in: PayPal checks the signature against the exact bytes it sent.
    body = f'{json.dumps(fields)[:-1]}, "webhook_event": {raw_event}}}'
    try:
        result = post(VERIFY_PATH, body)
    except httpx.HTTPStatusError as exc:
        # PayPal answers a malformed signature with a 4xx rather than a FAILURE status.
        if exc.request.url.path == VERIFY_PATH and exc.response.status_code < 500:
            return False
        raise
    return result.get("verification_status") == "SUCCESS"


def _signed_json_object(request) -> dict | None:
    """return(None): too large, missing a signature header, or not a json object."""
    if len(request.body) > MAX_WEBHOOK_BYTES:
        return None
    if not all(request.META.get(header) for header in _SIGNATURE_HEADERS.values()):
        return None
    try:
        event = json.loads(request.body.decode())
    except ValueError:
        return None
    return event if isinstance(event, dict) else None


@router.post(
    "/paypal/webhook/",
    response={200: None, frozenset({400, 429, 502, 503}): ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="120/m")
def paypal_webhook(request):
    if not paypal_configured() or not settings.PAYPAL_WEBHOOK_ID:
        return Status(503, {"detail": "paypal is not configured"})
    event = _signed_json_object(request)
    if event is None:
        return Status(400, {"detail": "webhook is malformed"})
    raw_event = request.body.decode()
    try:
        verified = _signature_verified(request, raw_event)
    except httpx.HTTPError:
        logger.exception("paypal_webhook_verify_failed")
        return Status(502, {"detail": "paypal is unavailable"})
    if not verified:
        logger.warning("paypal_webhook_unverified", extra={"event_id": event.get("id")})
        return Status(400, {"detail": "webhook signature is invalid"})
    if event.get("event_type") == CAPTURE_COMPLETED_EVENT:
        record_capture(request, event.get("resource") or {})
    return Status(200, None)
