"""Event text-blast endpoints + inbound Twilio webhook.

Send / list / detail are host-only (creator + accepted co-hosts). The webhook
is unauthenticated but signature-validated against TWILIO_AUTH_TOKEN.

Helpers live in `_event_blast_helpers.py` to keep this module focused on
HTTP shapes.
"""

import logging
from datetime import datetime
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from notifications.service import create_text_blast_failures_notification
from pydantic import Field

from community._event_blast_helpers import (
    MAX_BLASTS_PER_EVENT,
    can_send_event_blast,
    compose_outbound_body,
    create_blast_with_deliveries,
    event_blast_count,
    find_inbound_event,
    mask_phone,
    resolve_recipients,
    send_blast_to_recipients,
    validate_filters,
)
from community._field_limits import FieldLimit
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventBlastMute, EventStatus, EventTextBlast

router = Router()
webhook_router = Router()


# ─── schemas ───────────────────────────────────────────────────────────────


class TextBlastIn(Schema):
    message: str = Field(..., min_length=1, max_length=FieldLimit.DESCRIPTION)
    recipient_filters: list[str] = Field(..., min_length=1)


class TextBlastDeliveryOut(Schema):
    user_id: str | None
    user_name: str
    phone_number_masked: str
    status: str
    error_message: str


class TextBlastOut(Schema):
    id: str
    sender_id: str | None
    sender_name: str
    message: str
    recipient_filters: list[str]
    recipient_count: int
    sent_at: datetime
    deliveries: list[TextBlastDeliveryOut] = []


class TextBlastListOut(Schema):
    blasts: list[TextBlastOut]
    blasts_remaining: int  # MAX_BLASTS_PER_EVENT - current count, never < 0


# ─── shaping ────────────────────────────────────────────────────────────────


def _delivery_out(delivery) -> TextBlastDeliveryOut:
    name = (
        delivery.recipient.display_name or delivery.recipient.phone_number
        if delivery.recipient
        else "(deleted user)"
    )
    return TextBlastDeliveryOut(
        user_id=str(delivery.recipient_id) if delivery.recipient_id else None,
        user_name=name,
        phone_number_masked=mask_phone(delivery.phone_number),
        status=delivery.status,
        error_message=delivery.error_message,
    )


def _blast_out(blast: EventTextBlast, *, include_deliveries: bool) -> TextBlastOut:
    sender_name = (
        (blast.sender.display_name or blast.sender.phone_number)
        if blast.sender
        else "(deleted user)"
    )
    deliveries = []
    if include_deliveries:
        deliveries = [_delivery_out(d) for d in blast.deliveries.select_related("recipient").all()]
    return TextBlastOut(
        id=str(blast.id),
        sender_id=str(blast.sender_id) if blast.sender_id else None,
        sender_name=sender_name,
        message=blast.message,
        recipient_filters=list(blast.recipient_filters),
        recipient_count=blast.recipient_count,
        sent_at=blast.sent_at,
        deliveries=deliveries,
    )


# ─── permission / event helpers ─────────────────────────────────────────────


def _load_event_with_hosts(event_id: UUID) -> Event:
    return get_object_or_404(
        Event.objects.select_related("created_by").prefetch_related("co_hosts"),
        id=event_id,
    )


def _assert_can_send(event: Event, user) -> None:
    co_host_ids = {str(uid) for uid in event.co_hosts.values_list("pk", flat=True)}
    if not can_send_event_blast(user, event.created_by, co_host_ids):
        raise_validation(Code.TextBlast.NOT_HOST, status_code=403)


def _assert_event_active(event: Event) -> None:
    if event.status == EventStatus.CANCELLED:
        raise_validation(Code.TextBlast.EVENT_CANCELLED, status_code=400)


def _assert_under_lifetime_cap(event: Event) -> None:
    if event_blast_count(event) >= MAX_BLASTS_PER_EVENT:
        raise_validation(
            Code.TextBlast.EVENT_LIMIT_REACHED,
            status_code=400,
            limit=MAX_BLASTS_PER_EVENT,
        )


# ─── endpoints ──────────────────────────────────────────────────────────────


@router.post(
    "/events/{event_id}/text-blasts/",
    response={
        200: TextBlastOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
        429: ErrorOut,
    },
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="5/h")
def send_text_blast(request, event_id: UUID, payload: TextBlastIn):
    event = _load_event_with_hosts(event_id)
    _assert_can_send(event, request.auth)
    _assert_event_active(event)
    _assert_under_lifetime_cap(event)
    validate_filters(payload.recipient_filters)

    recipients = resolve_recipients(event, payload.recipient_filters, request.auth)
    if not recipients:
        raise_validation(Code.TextBlast.NO_RECIPIENTS, status_code=400)

    blast = create_blast_with_deliveries(
        event, request.auth, payload.message, payload.recipient_filters, recipients
    )
    sender_name = request.auth.display_name or request.auth.phone_number
    body = compose_outbound_body(payload.message, sender_name)

    failure_count = send_blast_to_recipients(blast, body)
    if failure_count > 0:
        create_text_blast_failures_notification(event, request.auth, failure_count)

    audit_log(
        logging.INFO,
        "text_blast.sent",
        request,
        target_type="event",
        target_id=str(event.id),
        details={
            "blast_id": str(blast.id),
            "recipient_count": blast.recipient_count,
            "failure_count": failure_count,
        },
    )
    return Status(200, _blast_out(blast, include_deliveries=True))


@router.get(
    "/events/{event_id}/text-blasts/",
    response={200: TextBlastListOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def list_text_blasts(request, event_id: UUID):
    event = _load_event_with_hosts(event_id)
    _assert_can_send(event, request.auth)

    blasts = (
        EventTextBlast.objects.filter(event=event).select_related("sender").order_by("-sent_at")
    )
    out = TextBlastListOut(
        blasts=[_blast_out(b, include_deliveries=False) for b in blasts],
        blasts_remaining=max(0, MAX_BLASTS_PER_EVENT - blasts.count()),
    )
    return Status(200, out)


@router.get(
    "/events/{event_id}/text-blasts/{blast_id}/",
    response={200: TextBlastOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_text_blast_detail(request, event_id: UUID, blast_id: UUID):
    event = _load_event_with_hosts(event_id)
    _assert_can_send(event, request.auth)

    blast = get_object_or_404(
        EventTextBlast.objects.select_related("sender", "event"),
        id=blast_id,
        event_id=event_id,
    )
    return Status(200, _blast_out(blast, include_deliveries=True))


# ─── inbound webhook ────────────────────────────────────────────────────────


@webhook_router.post(
    "/twilio/inbound/",
    response={200: str, 403: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="100/m")
def twilio_inbound(request: HttpRequest):
    """Receive an inbound SMS from Twilio. Signature-validated.

    On "M" body: mute the most-recent event the sender received a blast for,
    then reply with TwiML confirming the mute. Anything else: empty TwiML
    (Twilio's native STOP keyword handles full-account opt-out at the
    carrier layer, before our webhook even fires).
    """
    if not _validate_twilio_signature(request):
        raise_validation(Code.Perm.DENIED, status_code=403, action="twilio_inbound")

    body = (request.POST.get("Body") or "").strip().lower()
    from_phone = request.POST.get("From") or ""
    if body != "m" or not from_phone:
        return HttpResponse("<Response/>", content_type="application/xml")

    return HttpResponse(
        _handle_mute_request(from_phone),
        content_type="application/xml",
    )


def _validate_twilio_signature(request: HttpRequest) -> bool:
    """Verify the X-Twilio-Signature header against TWILIO_AUTH_TOKEN."""
    if not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_INBOUND_WEBHOOK_URL:
        return False
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False
    from twilio.request_validator import RequestValidator

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(
        settings.TWILIO_INBOUND_WEBHOOK_URL,
        dict(request.POST.items()),
        signature,
    )


def _handle_mute_request(from_phone: str) -> str:
    """Look up the user + recent blast for this phone, create a mute, return TwiML."""
    from users.models import User

    user = User.objects.filter(phone_number=from_phone).first()
    blast, _delivery = find_inbound_event(from_phone)

    if user is None or blast is None or blast.event.status == EventStatus.DELETED:
        return "<Response/>"

    EventBlastMute.objects.get_or_create(event=blast.event, user=user)
    title = blast.event.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<Response><Message>you\'re muted for "{title}" 🌿</Message></Response>'
