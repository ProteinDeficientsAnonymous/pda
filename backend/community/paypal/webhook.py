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
    result = post("/v1/notifications/verify-webhook-signature", body)
    return result.get("verification_status") == "SUCCESS"


@router.post(
    "/paypal/webhook/",
    response={200: None, frozenset({400, 429, 502, 503}): ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="120/m")
def paypal_webhook(request):
    if not paypal_configured() or not settings.PAYPAL_WEBHOOK_ID:
        return Status(503, {"detail": "paypal is not configured"})
    if len(request.body) > MAX_WEBHOOK_BYTES:
        return Status(400, {"detail": "webhook too large"})
    try:
        raw_event = request.body.decode()
        event = json.loads(raw_event)
    except ValueError:
        event = None
    if not isinstance(event, dict):
        return Status(400, {"detail": "webhook is not a json object"})
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
